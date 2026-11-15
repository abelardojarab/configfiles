# code-server with the tools this setup needs baked in, instead of
# installed at every start: python3 for review-kit's git hooks; GCC,
# LLVM/Clang 18, build tools, debuggers and analyzers for building and
# linting in the editor; Mull and mutmut for mutation testing; Node and uv
# for the MCP servers in the chat's mcp.json.
#
# Rebuild to pick up a new code-server or new packages (Watchtower cannot
# update a locally built image; systemd/code-server-rebuild.timer does
# this weekly):
#   docker compose build --pull code-server
#   docker compose up -d code-server
FROM linuxserver/code-server:latest

# Lets the weekly rebuild prune this image's old copies and nothing else.
LABEL configfiles.image=code-server-tools

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3 python3-venv \
      build-essential cmake ninja-build pkg-config ccache bear \
      gdb lldb valgrind \
      clang clangd clang-format clang-tidy lld llvm \
      cppcheck shellcheck \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Mull, pinned: the core package and its plugin for LLVM 18, matching
# Ubuntu 24.04's clang. Each is checked against the SHA-256 that GitHub
# publishes for the release asset.
ARG MULL_VERSION=0.36.0
ARG MULL_URL=https://github.com/mull-project/mull/releases/download
ARG MULL_CORE=Mull-0.36.0-ubuntu-amd64-24.04.deb
ARG CORE_SHA256=a978ea47f3bf8f8d66cb7df657551b2da69456ebfc92a752db127a68f9380796
ARG MULL_18=Mull-18-0.36.0-LLVM-18.1.3-ubuntu-amd64-24.04.deb
ARG M18_SHA256=e37ddcd8fa91e40c164cafa56587371483d0358d145c5f55fec8e8335c925d34

RUN cd /tmp \
 && curl -fsSL -o mull-core.deb "${MULL_URL}/${MULL_VERSION}/${MULL_CORE}" \
 && curl -fsSL -o mull-18.deb "${MULL_URL}/${MULL_VERSION}/${MULL_18}" \
 && printf '%s  %s\n' "${CORE_SHA256}" mull-core.deb \
      "${M18_SHA256}" mull-18.deb | sha256sum -c - \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      ./mull-core.deb ./mull-18.deb \
 && rm -f mull-core.deb mull-18.deb \
 && rm -rf /var/lib/apt/lists/*

# Ubuntu's Node is 18, too old for the MCP servers; nodejs-wheel brings a
# current one. A venv keeps these out of the system Python, and only the
# tools are linked onto PATH: putting the venv itself first would shadow
# python3 and pip with a root-owned venv the editor user cannot install
# into.
RUN python3 -m venv /opt/tools \
 && /opt/tools/bin/pip install --no-cache-dir uv nodejs-wheel mutmut \
 && for tool in node npm npx uv uvx mutmut; do \
      ln -s "/opt/tools/bin/$tool" "/usr/local/bin/$tool"; \
    done
