# Thin wrapper around the upstream agent-canvas image, adding uv/uvx so its
# MCP "fetch" server can be `uvx mcp-server-fetch` instead of
# @tokenizin/mcp-npx-fetch (which has no output-size limit and was dumping
# entire fetched pages -- tens of thousands of tokens -- straight into the
# conversation, see 2026-08-20 slow-Telegram-reply investigation).
# `COPY --from=` of astral-sh's official uv image is their documented
# Docker-install method: just the static binaries, no extra layers.
FROM ghcr.io/openhands/agent-canvas:1.13.0
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
