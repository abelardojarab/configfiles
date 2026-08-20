"""Telegram / Discord bridge into the OpenHands (agent-canvas) orchestrator.

Each allow-listed chat/channel gets its own long-lived OpenHands
conversation (created lazily, id cached in CONVERSATIONS_STATE_FILE).
Every inbound message is sent into that conversation with run=True, the
bridge polls execution_status until the agent goes idle, then relays
agent_final_response back to the chat.

Commands: /model [name] (list/switch LLM profile), /status (non-blocking
conversation status -- works even mid-run), /restart (stop + forget this
chat's conversation so the next message starts fresh). /status and /restart
deliberately skip the per-chat lock ask() holds, so they still respond while
a turn is slow or stuck.

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

    def pop(self, key: str) -> str | None:
        conversation_id = self._data.pop(key, None)
        if conversation_id is not None:
            self._path.write_text(json.dumps(self._data))
        return conversation_id


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

    async def _ensure_conversation(self, store: ConversationStore, chat_key: str) -> str:
        conversation_id = store.get(chat_key)
        if conversation_id is None or not await self._conversation_is_valid(conversation_id):
            conversation_id = await self._create_conversation()
            store.set(chat_key, conversation_id)
            log.info("chat=%s -> new conversation %s", chat_key, conversation_id)
        return conversation_id

    async def switch_model(self, store: ConversationStore, chat_key: str, profile_name: str) -> str:
        """Switch chat_key's conversation to a named LLM profile (see /api/profiles)."""
        async with self._lock_for(chat_key):
            conversation_id = await self._ensure_conversation(store, chat_key)
            resp = await self._client.post(
                f"/api/conversations/{conversation_id}/switch_profile",
                json={"profile_name": profile_name},
            )
            if resp.status_code == 404:
                return f"No such profile '{profile_name}'. Use /model to list available profiles."
            resp.raise_for_status()
            return f"Switched to profile '{profile_name}'."

    async def list_profiles(self) -> str:
        resp = await self._client.get("/api/profiles")
        resp.raise_for_status()
        data = resp.json()
        lines = [f"- {p['name']} ({p['model']})" for p in data.get("profiles", [])]
        active = data.get("active_profile")
        header = f"Available profiles (server default: {active}):"
        return "\n".join([header, *lines, "", "Usage: /model <name>"])

    async def status(self, store: ConversationStore, chat_key: str) -> str:
        """Report this chat's conversation state without waiting on it.

        Deliberately does not take the per-chat lock (unlike ask/switch_model)
        so it still answers while a slow/stuck ask() is holding that lock --
        that's the whole point of a status check.
        """
        conversation_id = store.get(chat_key)
        if conversation_id is None:
            return "No conversation yet for this chat -- send a message to start one."

        resp = await self._client.get(f"/api/conversations/{conversation_id}")
        if resp.status_code == 404:
            return "The stored conversation no longer exists -- it'll be recreated on your next message."
        resp.raise_for_status()
        data = resp.json()

        execution_status = data.get("execution_status", "unknown")
        metrics = data.get("stats", {}).get("usage_to_metrics", {}).get("default", {})
        model = metrics.get("model_name", "unknown")
        prompt_tokens = metrics.get("accumulated_token_usage", {}).get("prompt_tokens", 0)
        latencies = metrics.get("response_latencies", [])
        last_latency = latencies[-1]["latency"] if latencies else None

        lines = [
            f"status: {execution_status}",
            f"model: {model}",
            f"accumulated prompt tokens: {prompt_tokens:,}",
        ]
        if last_latency is not None:
            lines.append(f"last turn latency: {last_latency:.1f}s")
        if execution_status == "running":
            lines.append("still working -- use /restart if you want to abandon this and start fresh.")
        return "\n".join(lines)

    async def restart(self, store: ConversationStore, chat_key: str) -> str:
        """Stop and forget this chat's conversation; the next message starts a new one.

        Does not take the per-chat lock -- must work even while a stuck ask()
        is holding it, otherwise /restart could never interrupt a stuck run.
        """
        conversation_id = store.pop(chat_key)
        if conversation_id is None:
            return "No conversation to restart -- your next message will start a fresh one anyway."
        try:
            await self._client.post(f"/api/conversations/{conversation_id}/goal/stop")
        except Exception:
            log.exception("Failed to stop conversation %s before restart", conversation_id)
        return "Stopped and forgot this chat's conversation. Your next message starts a fresh one."

    async def ask(self, store: ConversationStore, chat_key: str, text: str) -> str:
        """Send `text` into the conversation mapped to chat_key, wait for the reply."""
        async with self._lock_for(chat_key):
            conversation_id = await self._ensure_conversation(store, chat_key)

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


async def handle_model_command(client: OpenHandsClient, store: ConversationStore, chat_key: str, arg: str) -> str:
    """`/model` with no argument lists profiles; `/model <name>` switches this chat to it."""
    arg = arg.strip()
    if not arg:
        return await client.list_profiles()
    return await client.switch_model(store, chat_key, arg)


async def run_telegram(client: OpenHandsClient, store: ConversationStore):
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

    def _allowed(chat_id: int) -> bool:
        if TELEGRAM_ALLOWED_CHAT_IDS and chat_id not in TELEGRAM_ALLOWED_CHAT_IDS:
            log.warning("Telegram: dropping message from unlisted chat_id=%s", chat_id)
            return False
        return True

    async def on_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        arg = " ".join(context.args) if context.args else ""
        try:
            reply = await handle_model_command(client, store, f"telegram:{chat.id}", arg)
        except Exception:
            log.exception("Telegram: /model failed")
            reply = "(/model call failed -- see chat-bridge logs)"
        await message.reply_text(reply)

    async def on_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        try:
            reply = await client.status(store, f"telegram:{chat.id}")
        except Exception:
            log.exception("Telegram: /status failed")
            reply = "(/status call failed -- see chat-bridge logs)"
        await message.reply_text(reply)

    async def on_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        try:
            reply = await client.restart(store, f"telegram:{chat.id}")
        except Exception:
            log.exception("Telegram: /restart failed")
            reply = "(/restart call failed -- see chat-bridge logs)"
        await message.reply_text(reply)

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not message.text or not _allowed(chat.id):
            return

        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        try:
            reply = await client.ask(store, f"telegram:{chat.id}", message.text)
        except Exception:
            log.exception("Telegram: orchestrator call failed")
            reply = "(orchestrator call failed -- see chat-bridge logs)"

        for part in chunk(reply, 4000):
            await message.reply_text(part)

    # concurrent_updates: PTB's default (SimpleUpdateProcessor,
    # max_concurrent_updates=1) processes updates strictly one at a time, so
    # /status or /restart sent while on_message is still awaiting a slow
    # ask() would sit queued behind it and never run -- defeating the point
    # of a status check. status()/restart() skip OpenHandsClient's own
    # per-chat lock for the same reason; this is the other half of that fix.
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(8).build()
    app.add_handler(CommandHandler("model", on_model))
    app.add_handler(CommandHandler("status", on_status))
    app.add_handler(CommandHandler("restart", on_restart))
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

        if message.content.startswith("/model"):
            arg = message.content[len("/model"):].strip()
            try:
                reply = await handle_model_command(client, store, f"discord:{message.channel.id}", arg)
            except Exception:
                log.exception("Discord: /model failed")
                reply = "(/model call failed -- see chat-bridge logs)"
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        if message.content.startswith("/status"):
            try:
                reply = await client.status(store, f"discord:{message.channel.id}")
            except Exception:
                log.exception("Discord: /status failed")
                reply = "(/status call failed -- see chat-bridge logs)"
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        if message.content.startswith("/restart"):
            try:
                reply = await client.restart(store, f"discord:{message.channel.id}")
            except Exception:
                log.exception("Discord: /restart failed")
                reply = "(/restart call failed -- see chat-bridge logs)"
            for part in chunk(reply, 1900):
                await message.channel.send(part)
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
