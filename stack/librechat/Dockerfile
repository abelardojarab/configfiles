# Thin wrapper around the upstream LibreChat image, adding a passwd entry for
# uid/gid 501 (the arbitrary-uid pattern this image runs as, set via `user:
# "501:501"` in docker-compose.yml). Without an entry, any MCP server that
# calls Node's os.userInfo() (libuv's uv_os_get_passwd, e.g.
# @mkusaka/mcp-shell-server) crashes with ERR_SYSTEM_ERROR/ENOENT at startup
# -- /etc/passwd is root:root 644 in the base image, not writable by 501 at
# runtime, so this has to be baked in at build time instead. HOME=/tmp
# matches the NPM_CONFIG_CACHE/HOME=/tmp workaround already used elsewhere in
# librechat.yaml for the same uid-with-no-passwd-entry root cause.
FROM registry.librechat.ai/danny-avila/librechat-dev:latest
USER root
RUN echo "abelardojara:x:501:501::/tmp:/bin/sh" >> /etc/passwd
# Patch updateMCPServerTools to return tools instead of null when cache fencing fails for MCP servers
RUN sed -i '/async function updateMCPServerTools/,/async function mergeAppTools/ s/return null;/return serverTools;/g' /app/node_modules/@librechat/api/dist/index.cjs
USER 501
