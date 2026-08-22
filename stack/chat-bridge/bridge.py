"""Telegram / Discord bridge into the OpenHands (agent-canvas) orchestrator.

Each allow-listed chat/channel gets its own long-lived OpenHands
conversation (created lazily, id cached in CONVERSATIONS_STATE_FILE).
Every inbound message is sent into that conversation with run=True, the
bridge polls execution_status until the agent goes idle, then relays
agent_final_response back to the chat.

Commands: /model [name] (list/switch this chat's LLM profile, always prints
which one is active), /agent [name] (list/switch this chat's agent profile --
e.g. default vs orchestrator-gemini vs orchestrator-qwen -- always prints
which one is active), /status (non-blocking conversation status -- works even
mid-run), /restart (stop + forget this chat's conversation so the next
message starts fresh). None of /model, /agent, /status, or /restart take the
per-chat lock ask() holds, so all four still work as an escape hatch while a
turn is slow or stuck instead of queuing silently behind it.

Switching agent profile changes the whole agent/LLM/MCP setup, so /agent
stops and forgets this chat's current conversation (like /restart) and
remembers the chosen profile in ConversationStore -- the next message starts
a fresh conversation launched on that profile. It stays sticky across
/restart too, until /agent picks something else.

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
    """Persists per-chat state (OpenHands conversation_id + chosen agent
    profile name) across bridge restarts.

    Older state files store a flat chat_key -> conversation_id string; those
    entries are upgraded to {"conversation_id": ...} in memory on load and
    rewritten in the new shape on the next save.
    """

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        raw: dict = json.loads(path.read_text()) if path.exists() else {}
        self._data: dict[str, dict] = {
            key: (value if isinstance(value, dict) else {"conversation_id": value})
            for key, value in raw.items()
        }

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data))

    def get_conversation(self, key: str) -> str | None:
        return self._data.get(key, {}).get("conversation_id")

    def set_conversation(self, key: str, conversation_id: str) -> None:
        self._data.setdefault(key, {})["conversation_id"] = conversation_id
        self._save()

    def pop_conversation(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        conversation_id = entry.pop("conversation_id", None)
        if not entry:
            self._data.pop(key, None)
        if conversation_id is not None:
            self._save()
        return conversation_id

    def get_agent_profile(self, key: str) -> str | None:
        """This chat's explicitly-chosen agent profile name, or None to use
        the OpenHands server's active_agent_profile_id default."""
        return self._data.get(key, {}).get("agent_profile")

    def set_agent_profile(self, key: str, name: str) -> None:
        self._data.setdefault(key, {})["agent_profile"] = name
        self._save()


class OpenHandsClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=OPENHANDS_BASE_URL,
            headers={"X-Session-API-Key": load_api_key()},
            # OpenHands' API goes unresponsive to ALL requests -- not just
            # the busy conversation's -- for 1-2+ minutes while a turn is
            # running (observed 2026-08-21: 100s+ stretches with zero log
            # activity server-side, not a slow-but-progressing call). A flat
            # 30s timeout turned that normal busy period into hard failures
            # on /model, /agent, /status. Keep connect fast-failing (a dead
            # container should error quickly) but give reads real headroom.
            timeout=httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0),
        )
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())

    async def _agent_profiles(self) -> dict:
        resp = await self._client.get("/api/agent-profiles")
        resp.raise_for_status()
        return resp.json()

    async def _active_agent_profile_id(self) -> str:
        data = await self._agent_profiles()
        profile_id = data.get("active_agent_profile_id")
        if not profile_id:
            raise RuntimeError("No active agent profile configured in agent-canvas")
        return profile_id

    async def _resolve_agent_profile_id(self, store: ConversationStore, chat_key: str) -> str:
        """This chat's /agent-chosen profile id, or the server default's."""
        name = store.get_agent_profile(chat_key)
        if name is None:
            return await self._active_agent_profile_id()
        data = await self._agent_profiles()
        for p in data.get("profiles", []):
            if p["name"] == name:
                return p["id"]
        # Chosen profile got deleted server-side since -- fall back rather
        # than fail the conversation outright.
        log.warning("chat=%s: stored agent profile '%s' no longer exists, using server default", chat_key, name)
        return await self._active_agent_profile_id()

    async def _create_conversation(self, store: ConversationStore, chat_key: str) -> str:
        resp = await self._client.post(
            "/api/conversations",
            json={
                "workspace": {"kind": "LocalWorkspace", "working_dir": OPENHANDS_WORKSPACE},
                "agent_profile_id": await self._resolve_agent_profile_id(store, chat_key),
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def _conversation_is_valid(self, conversation_id: str) -> bool:
        resp = await self._client.get(f"/api/conversations/{conversation_id}")
        return resp.status_code == 200

    async def _ensure_conversation(self, store: ConversationStore, chat_key: str) -> str:
        conversation_id = store.get_conversation(chat_key)
        if conversation_id is None or not await self._conversation_is_valid(conversation_id):
            conversation_id = await self._create_conversation(store, chat_key)
            store.set_conversation(chat_key, conversation_id)
            log.info("chat=%s -> new conversation %s", chat_key, conversation_id)
        return conversation_id

    async def _live_state(self, conversation_id: str) -> tuple[str | None, str | None]:
        """Best-effort (active_model, active_agent_profile_name) for a live
        conversation, read straight off its own record rather than guessed
        from usage-metrics keys (see status()'s comment for why that's
        unreliable)."""
        resp = await self._client.get(f"/api/conversations/{conversation_id}")
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        model = data.get("agent", {}).get("llm", {}).get("model")
        agent_profile_name = None
        launched = data.get("launched_agent_profile")
        if launched:
            profiles = await self._agent_profiles()
            agent_profile_name = next(
                (p["name"] for p in profiles.get("profiles", []) if p["id"] == launched["agent_profile_id"]),
                launched["agent_profile_id"],
            )
        return model, agent_profile_name

    async def switch_model(self, store: ConversationStore, chat_key: str, profile_name: str) -> str:
        """Switch chat_key's conversation to a named LLM profile (see /api/profiles).

        Deliberately does not take the per-chat lock ask() holds -- same
        reasoning as status()/restart(): switching model/agent is often
        exactly what someone reaches for to get *out* of a stuck or slow
        turn (e.g. one retrying against a rate-limited backend), so it must
        still work while ask() is holding that lock, not queue silently
        behind it (observed 2026-08-21: /model and /agent both sat waiting
        with zero feedback behind a turn stuck on a cooling-down provider).
        """
        conversation_id = await self._ensure_conversation(store, chat_key)
        resp = await self._client.post(
            f"/api/conversations/{conversation_id}/switch_profile",
            json={"profile_name": profile_name},
        )
        if resp.status_code == 404:
            return f"No such profile '{profile_name}'. Use /model to list available profiles."
        resp.raise_for_status()
        return f"Active model for this chat: {profile_name}"

    async def list_profiles(self, store: ConversationStore, chat_key: str) -> str:
        resp = await self._client.get("/api/profiles")
        resp.raise_for_status()
        data = resp.json()
        lines = [f"- {p['name']} ({p['model']})" for p in data.get("profiles", [])]
        server_default = data.get("active_profile")

        conversation_id = store.get_conversation(chat_key)
        active_model = (await self._live_state(conversation_id))[0] if conversation_id else None
        active_line = (
            f"Active model for this chat: {active_model}"
            if active_model
            else "No conversation yet for this chat -- your next message starts one on the active agent profile's default model."
        )

        header = f"Available profiles (server default: {server_default}):"
        return "\n".join([header, *lines, "", active_line, "Usage: /model <name>"])

    async def switch_agent(self, store: ConversationStore, chat_key: str, profile_name: str) -> str:
        """Switch chat_key to a named agent profile (see /api/agent-profiles).

        Unlike switch_model, this can't be applied to a live conversation --
        the agent/LLM/MCP setup is fixed at conversation creation
        (agent_profile_id). So this stops and forgets the current
        conversation (same as /restart) and remembers the choice; the next
        message launches a fresh conversation on the new profile.

        Deliberately does not take the per-chat lock ask() holds -- see the
        comment on switch_model for why: this needs to work as an escape
        hatch while a turn is stuck, not queue behind it.
        """
        data = await self._agent_profiles()
        match = next((p for p in data.get("profiles", []) if p["name"] == profile_name), None)
        if match is None:
            return f"No such agent profile '{profile_name}'. Use /agent to list available agent profiles."

        old_conversation_id = store.pop_conversation(chat_key)
        if old_conversation_id:
            try:
                await self._client.post(f"/api/conversations/{old_conversation_id}/goal/stop")
            except Exception:
                log.exception("Failed to stop conversation %s before agent switch", old_conversation_id)

        store.set_agent_profile(chat_key, profile_name)
        return f"Active agent for this chat: {profile_name} (next message starts a fresh conversation on it)"

    async def list_agent_profiles(self, store: ConversationStore, chat_key: str) -> str:
        data = await self._agent_profiles()
        lines = [f"- {p['name']} (llm: {p['llm_profile_ref']})" for p in data.get("profiles", [])]
        active_id = data.get("active_agent_profile_id")
        server_default_name = next(
            (p["name"] for p in data.get("profiles", []) if p["id"] == active_id), active_id
        )

        conversation_id = store.get_conversation(chat_key)
        live_agent_name = (await self._live_state(conversation_id))[1] if conversation_id else None
        chosen = store.get_agent_profile(chat_key)
        active_name = live_agent_name or chosen or server_default_name

        header = f"Available agent profiles (server default: {server_default_name}):"
        active_line = f"Active agent for this chat: {active_name}"
        return "\n".join([header, *lines, "", active_line, "Usage: /agent <name>"])

    async def status(self, store: ConversationStore, chat_key: str) -> str:
        """Report this chat's conversation state without waiting on it.

        Deliberately does not take the per-chat lock (unlike ask/switch_model)
        so it still answers while a slow/stuck ask() is holding that lock --
        that's the whole point of a status check.
        """
        conversation_id = store.get_conversation(chat_key)
        if conversation_id is None:
            return "No conversation yet for this chat -- send a message to start one."

        resp = await self._client.get(f"/api/conversations/{conversation_id}")
        if resp.status_code == 404:
            return "The stored conversation no longer exists -- it'll be recreated on your next message."
        resp.raise_for_status()
        data = resp.json()

        execution_status = data.get("execution_status", "unknown")
        model = data.get("agent", {}).get("llm", {}).get("model", "unknown")

        # stats.usage_to_metrics is keyed by the LLM profile's usage_id (e.g.
        # "gemini-cli-proxy"), not a fixed "default" -- match on model_name
        # instead of assuming a key, otherwise this silently returns {} (and
        # thus 0 tokens/no latency) for every profile except literally
        # "default". Confirmed live 2026-08-21: a gemini-cli-proxy
        # conversation's usage_to_metrics key was "gemini-cli-proxy".
        metrics_by_key = data.get("stats", {}).get("usage_to_metrics", {})
        metrics = next(
            (m for m in metrics_by_key.values() if m.get("model_name") == model),
            {},
        )
        prompt_tokens = metrics.get("accumulated_token_usage", {}).get("prompt_tokens", 0)
        latencies = metrics.get("response_latencies", [])
        last_latency = latencies[-1]["latency"] if latencies else None

        agent_profile_name = None
        launched = data.get("launched_agent_profile")
        if launched:
            profiles = await self._agent_profiles()
            agent_profile_name = next(
                (p["name"] for p in profiles.get("profiles", []) if p["id"] == launched["agent_profile_id"]),
                launched["agent_profile_id"],
            )

        lines = [
            f"status: {execution_status}",
            f"model: {model}",
            f"agent profile: {agent_profile_name or 'unknown'}",
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
        Leaves this chat's /agent-chosen profile (if any) in place -- it's
        sticky across restarts, only /agent changes it.
        """
        conversation_id = store.pop_conversation(chat_key)
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
                try:
                    status_resp = await self._client.get(f"/api/conversations/{conversation_id}")
                    status_resp.raise_for_status()
                except httpx.TimeoutException:
                    # A status check timing out means the server is busy
                    # right now, not that the turn failed -- keep polling
                    # instead of blowing up the whole ask() over it.
                    continue
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


async def _safe_call(coro, log_prefix: str, label: str) -> str:
    """Run a command coroutine, distinguishing "OpenHands is busy" from an
    actual failure -- see the timeout comment on OpenHandsClient's httpx
    client for why the former is common and not a real error."""
    try:
        return await coro
    except httpx.TimeoutException:
        log.warning("%s: OpenHands didn't respond in time (likely still busy with a previous turn)", log_prefix)
        return f"({label} call timed out -- OpenHands looks busy with a previous turn, try again in a moment)"
    except Exception:
        log.exception("%s failed", log_prefix)
        return f"({label} call failed -- see chat-bridge logs)"


async def handle_model_command(client: OpenHandsClient, store: ConversationStore, chat_key: str, arg: str) -> str:
    """`/model` with no argument lists profiles; `/model <name>` switches this chat to it."""
    arg = arg.strip()
    if not arg:
        return await client.list_profiles(store, chat_key)
    return await client.switch_model(store, chat_key, arg)


async def handle_agent_command(client: OpenHandsClient, store: ConversationStore, chat_key: str, arg: str) -> str:
    """`/agent` with no argument lists agent profiles; `/agent <name>` switches this chat to it."""
    arg = arg.strip()
    if not arg:
        return await client.list_agent_profiles(store, chat_key)
    return await client.switch_agent(store, chat_key, arg)


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
        reply = await _safe_call(
            handle_model_command(client, store, f"telegram:{chat.id}", arg),
            "Telegram: /model", "/model",
        )
        await message.reply_text(reply)

    async def on_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        arg = " ".join(context.args) if context.args else ""
        reply = await _safe_call(
            handle_agent_command(client, store, f"telegram:{chat.id}", arg),
            "Telegram: /agent", "/agent",
        )
        await message.reply_text(reply)

    async def on_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        reply = await _safe_call(
            client.status(store, f"telegram:{chat.id}"),
            "Telegram: /status", "/status",
        )
        await message.reply_text(reply)

    async def on_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not _allowed(chat.id):
            return
        reply = await _safe_call(
            client.restart(store, f"telegram:{chat.id}"),
            "Telegram: /restart", "/restart",
        )
        await message.reply_text(reply)

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.effective_message
        if chat is None or message is None or not message.text or not _allowed(chat.id):
            return

        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        reply = await _safe_call(
            client.ask(store, f"telegram:{chat.id}", message.text),
            "Telegram: orchestrator", "orchestrator",
        )

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
    app.add_handler(CommandHandler("agent", on_agent))
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
            reply = await _safe_call(
                handle_model_command(client, store, f"discord:{message.channel.id}", arg),
                "Discord: /model", "/model",
            )
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        if message.content.startswith("/agent"):
            arg = message.content[len("/agent"):].strip()
            reply = await _safe_call(
                handle_agent_command(client, store, f"discord:{message.channel.id}", arg),
                "Discord: /agent", "/agent",
            )
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        if message.content.startswith("/status"):
            reply = await _safe_call(
                client.status(store, f"discord:{message.channel.id}"),
                "Discord: /status", "/status",
            )
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        if message.content.startswith("/restart"):
            reply = await _safe_call(
                client.restart(store, f"discord:{message.channel.id}"),
                "Discord: /restart", "/restart",
            )
            for part in chunk(reply, 1900):
                await message.channel.send(part)
            return

        async with message.channel.typing():
            reply = await _safe_call(
                client.ask(store, f"discord:{message.channel.id}", message.content),
                "Discord: orchestrator", "orchestrator",
            )

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
