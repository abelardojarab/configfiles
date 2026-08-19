"""Telegram / Discord bridge into the OpenHands (agent-canvas) orchestrator.

Each allow-listed chat/channel gets its own long-lived OpenHands
conversation (created lazily, id cached in CONVERSATIONS_STATE_FILE).
Every inbound message is sent into that conversation with run=True, the
bridge polls execution_status until the agent goes idle, then relays
agent_final_response back to the chat.

Anyone who can message the bot can make the orchestrator run shell
commands, read/write the mounted workspace, and reach the docker socket
it has access to. ALLOWED_TELEGRAM_CHAT_IDS / ALLOWED_DISCORD_CHANNEL_IDS
are not a nicety here -- treat them like a root shell allow-list.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("chat-bridge")

OPENHANDS_BASE_URL = os.environ.get("OPENHANDS_BASE_URL", "http://openhands:8000")
OPENHANDS_API_KEY_FILE = os.environ.get("OPENHANDS_API_KEY_FILE", "/run/secrets/openhands-api-key")
OPENHANDS_WORKSPACE = os.environ.get("OPENHANDS_WORKSPACE", "/projects/workspace")
STATE_FILE = Path(os.environ.get("CONVERSATIONS_STATE_FILE", "/data/conversations.json"))

POLL_INTERVAL_SECS = 2.0
POLL_TIMEOUT_SECS = float(os.environ.get("OPENHANDS_POLL_TIMEOUT_SECS", "600"))
TERMINAL_STATUSES = {"idle", "finished", "error", "stuck"}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_CHAT_IDS = {
    int(x) for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if x.strip()
}

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
DISCORD_ALLOWED_CHANNEL_IDS = {
    int(x) for x in os.environ.get("DISCORD_ALLOWED_CHANNEL_IDS", "").split(",") if x.strip()
}


def load_api_key() -> str:
    return Path(OPENHANDS_API_KEY_FILE).read_text().strip()


class ConversationStore:
    """Persists chat-key -> OpenHands conversation_id across bridge restarts."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, conversation_id: str) -> None:
        self._data[key] = conversation_id
        self._path.write_text(json.dumps(self._data))


class OpenHandsClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=OPENHANDS_BASE_URL,
            headers={"X-Session-API-Key": load_api_key()},
            timeout=30.0,
        )
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())

    async def _active_agent_profile_id(self) -> str:
        resp = await self._client.get("/api/agent-profiles")
        resp.raise_for_status()
        profile_id = resp.json().get("active_agent_profile_id")
        if not profile_id:
            raise RuntimeError("No active agent profile configured in agent-canvas")
        return profile_id

    async def _create_conversation(self) -> str:
        resp = await self._client.post(
            "/api/conversations",
            json={
                "workspace": {"kind": "LocalWorkspace", "working_dir": OPENHANDS_WORKSPACE},
                "agent_profile_id": await self._active_agent_profile_id(),
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def _conversation_is_valid(self, conversation_id: str) -> bool:
        resp = await self._client.get(f"/api/conversations/{conversation_id}")
        return resp.status_code == 200

    async def ask(self, store: ConversationStore, chat_key: str, text: str) -> str:
        """Send `text` into the conversation mapped to chat_key, wait for the reply."""
        async with self._lock_for(chat_key):
            conversation_id = store.get(chat_key)
            if conversation_id is None or not await self._conversation_is_valid(conversation_id):
                conversation_id = await self._create_conversation()
                store.set(chat_key, conversation_id)
                log.info("chat=%s -> new conversation %s", chat_key, conversation_id)

            send_resp = await self._client.post(
                f"/api/conversations/{conversation_id}/events",
                json={"role": "user", "content": [{"type": "text", "text": text}], "run": True},
            )
            send_resp.raise_for_status()

            elapsed = 0.0
            while elapsed < POLL_TIMEOUT_SECS:
                await asyncio.sleep(POLL_INTERVAL_SECS)
                elapsed += POLL_INTERVAL_SECS
                status_resp = await self._client.get(f"/api/conversations/{conversation_id}")
                status_resp.raise_for_status()
                status = status_resp.json().get("execution_status")
                if status in TERMINAL_STATUSES:
                    break
            else:
                return "(orchestrator is still running after the timeout -- check the agent-canvas UI)"

            if status in ("error", "stuck"):
                return f"(agent hit status={status}; check the agent-canvas UI for details)"

            final_resp = await self._client.get(f"/api/conversations/{conversation_id}/agent_final_response")
            final_resp.raise_for_status()
            return final_resp.json().get("response") or "(no response text -- check the agent-canvas UI)"


def chunk(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


async def run_telegram(client: OpenHandsClient, store: ConversationStore):
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not message.text:
            return
        if TELEGRAM_ALLOWED_CHAT_IDS and chat.id not in TELEGRAM_ALLOWED_CHAT_IDS:
            log.warning("Telegram: dropping message from unlisted chat_id=%s", chat.id)
            return

        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        try:
            reply = await client.ask(store, f"telegram:{chat.id}", message.text)
        except Exception:
            log.exception("Telegram: orchestrator call failed")
            reply = "(orchestrator call failed -- see chat-bridge logs)"

        for part in chunk(reply, 4000):
            await message.reply_text(part)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    async with app:
        await app.start()
        await app.updater.start_polling()
        log.info("Telegram bridge running (allowed chats: %s)", TELEGRAM_ALLOWED_CHAT_IDS or "ANY -- unset!")
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()


async def run_discord(client: OpenHandsClient, store: ConversationStore):
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    dc = discord.Client(intents=intents)

    @dc.event
    async def on_ready():
        log.info(
            "Discord bridge running as %s (allowed channels: %s)",
            dc.user,
            DISCORD_ALLOWED_CHANNEL_IDS or "ANY -- unset!",
        )

    @dc.event
    async def on_message(message: "discord.Message"):
        if message.author == dc.user:
            return
        if DISCORD_ALLOWED_CHANNEL_IDS and message.channel.id not in DISCORD_ALLOWED_CHANNEL_IDS:
            log.warning("Discord: dropping message from unlisted channel_id=%s", message.channel.id)
            return
        if not message.content:
            return

        async with message.channel.typing():
            try:
                reply = await client.ask(store, f"discord:{message.channel.id}", message.content)
            except Exception:
                log.exception("Discord: orchestrator call failed")
                reply = "(orchestrator call failed -- see chat-bridge logs)"

        for part in chunk(reply, 1900):
            await message.channel.send(part)

    await dc.start(DISCORD_BOT_TOKEN)


async def main():
    if not TELEGRAM_BOT_TOKEN and not DISCORD_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and/or DISCORD_BOT_TOKEN")

    client = OpenHandsClient()
    store = ConversationStore(STATE_FILE)

    tasks = []
    if TELEGRAM_BOT_TOKEN:
        if not TELEGRAM_ALLOWED_CHAT_IDS:
            log.warning("TELEGRAM_ALLOWED_CHAT_IDS is empty -- ANYONE who messages this bot can drive the orchestrator")
        tasks.append(run_telegram(client, store))
    if DISCORD_BOT_TOKEN:
        if not DISCORD_ALLOWED_CHANNEL_IDS:
            log.warning("DISCORD_ALLOWED_CHANNEL_IDS is empty -- ANYONE in any server with this bot can drive the orchestrator")
        tasks.append(run_discord(client, store))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
