# code-server with the tools this setup needs baked in, instead of
# installed at every start: python3 (with venv and headers) for
# review-kit's git hooks and projects; GCC, LLVM/Clang 18, build
# tools, debuggers and analyzers; Go, Rust and Bazel; gRPC and
# protobuf tools (protoc and its plugins, grpcurl, buf); Mull and mutmut
# for mutation testing; the Docker CLI for the host's socket; Node and uv
# for the MCP servers in the chat's mcp.json; and everyday command-line
# tools.
#
# Every download that is not from Ubuntu's archive is pinned and checked
# against its published SHA-256 (Docker's apt key, against its published
# fingerprint).
#
# Rebuild to pick up a new code-server or new packages (Watchtower cannot
# update a locally built image; systemd/code-server-rebuild.timer does
# this weekly):
#   docker compose build --pull code-server
#   docker compose up -d code-server
FROM linuxserver/code-server:latest

# Lets the weekly rebuild prune this image's old copies and nothing else.
LABEL configfiles.image=code-server-tools

# The editor runs as abc with this UID (PUID in docker-compose.yml);
# tools the user must be able to update are owned by it.
ARG PUID=501
# The host's docker group, which owns /var/run/docker.sock.
ARG DOCKER_GID=135

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3 python3-venv python3-dev \
      build-essential cmake ninja-build pkg-config ccache bear \
      gdb lldb valgrind strace ltrace lsof \
      clang clangd clang-format clang-tidy lld llvm \
      cppcheck shellcheck \
      protobuf-compiler libprotobuf-dev libgrpc++-dev protobuf-compiler-grpc \
      git-lfs ripgrep fd-find tree file zip unzip zstd rsync wget \
      sqlite3 htop tmux vim bc yq \
      dnsutils iputils-ping tcpdump \
      curl ca-certificates gnupg \
 && ln -s /usr/bin/fdfind /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI, Compose and Buildx from Docker's apt repository (Ubuntu's
# docker.io would also bring a daemon). The key must match Docker's
# published fingerprint before the repository is trusted. abc joins a
# group with the host's docker GID so it can use the mounted socket.
ARG DOCKER_KEY_FPR=9DC858229FC7DD38854AE2D88D81803C0EBFCD88
RUN install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      -o /tmp/docker.asc \
 && gpg --show-keys --with-colons /tmp/docker.asc \
      | grep -q "^fpr:::::::::${DOCKER_KEY_FPR}:" \
 && mv /tmp/docker.asc /etc/apt/keyrings/docker.asc \
 && . /etc/os-release \
 && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc]" \
      "https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      docker-ce-cli docker-compose-plugin docker-buildx-plugin \
 && rm -rf /var/lib/apt/lists/* \
 && group=$(getent group "${DOCKER_GID}" | cut -d: -f1) \
 && if [ -z "$group" ]; then \
      group=dockerhost; groupadd -g "${DOCKER_GID}" "$group"; \
    fi \
 && usermod -aG "$group" abc

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

# Go from go.dev (Ubuntu's is 1.22). GOPATH stays the default ~/go, which
# is /config/go, on the persistent volume.
ARG GO_VERSION=1.27.3
ARG GO_SHA256=65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40
RUN curl -fsSL -o /tmp/go.tgz \
      "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
 && echo "${GO_SHA256}  /tmp/go.tgz" | sha256sum -c - \
 && tar -C /usr/local -xzf /tmp/go.tgz \
 && rm -f /tmp/go.tgz \
 && ln -s /usr/local/go/bin/go /usr/local/go/bin/gofmt /usr/local/bin/

# gRPC and protobuf tools for Go and the command line: the protoc
# plugins for Go messages and gRPC services, grpcurl to call a running
# server, and buf to lint protos and check for breaking changes. Each is
# a separate go install, since pinned versions of different modules cannot
# share one; go install checks each module against Go's checksum database
# (sum.golang.org), and GOTOOLCHAIN=local fails the build instead of
# fetching another Go.
ARG PROTOC_GEN_GO=google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.12
ARG PROTOC_GEN_GO_GRPC=google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.6.2
ARG GRPCURL=github.com/fullstorydev/grpcurl/cmd/grpcurl@v1.9.4
ARG BUF=github.com/bufbuild/buf/cmd/buf@v1.75.0
RUN for mod in "${PROTOC_GEN_GO}" "${PROTOC_GEN_GO_GRPC}" "${GRPCURL}" \
      "${BUF}"; do \
      GOBIN=/usr/local/bin GOPATH=/tmp/gopath GOCACHE=/tmp/gocache \
      GOTOOLCHAIN=local go install "$mod" || exit 1; \
    done \
 && rm -rf /tmp/gopath /tmp/gocache

# Bazel through bazelisk, which fetches the version each repository asks
# for, and buildifier, both from their GitHub releases.
ARG BZ_GH=https://github.com/bazelbuild
ARG BZ_ISK=bazelisk/releases/download/v1.30.0/bazelisk-linux-amd64
ARG BZ_ISK_SUM=a248ae2b2b62b5baebb748f6fba7203bff1a27e5d01b55399a8406744cb539e8
ARG BZ_FMT=buildtools/releases/download/v10.2.0/buildifier-linux-amd64
ARG BZ_FMT_SUM=470844069d710d0b7740e55007071c63e4d00be89a833dce5d1a91790e84dc28
RUN cd /tmp \
 && curl -fsSL -o bazel "${BZ_GH}/${BZ_ISK}" \
 && curl -fsSL -o buildifier "${BZ_GH}/${BZ_FMT}" \
 && printf '%s  %s\n' "${BZ_ISK_SUM}" bazel \
      "${BZ_FMT_SUM}" buildifier | sha256sum -c - \
 && install -m 0755 bazel buildifier /usr/local/bin/ \
 && rm -f bazel buildifier

# Rust through rustup, with the stable toolchain. Owned by the editor
# user so `rustup update` and `cargo install` work without root.
ARG RUSTUP_URL=https://static.rust-lang.org/rustup/archive
ARG RUSTUP_INIT=1.29.3/x86_64-unknown-linux-gnu/rustup-init
ARG RUSTUP_SUM=b1c8cb14e30889e7e2999e6b69e62d9e9b9ffc0f4df8180564d306d9680e6c55
ENV RUSTUP_HOME=/opt/rust/rustup \
    CARGO_HOME=/opt/rust/cargo
RUN curl -fsSL -o /tmp/rustup-init "${RUSTUP_URL}/${RUSTUP_INIT}" \
 && echo "${RUSTUP_SUM}  /tmp/rustup-init" | sha256sum -c - \
 && chmod +x /tmp/rustup-init \
 && /tmp/rustup-init -y --no-modify-path --profile minimal \
      --default-toolchain stable --component rustfmt,clippy \
 && rm -f /tmp/rustup-init \
 && chown -R "${PUID}:${PUID}" /opt/rust
ENV PATH=/opt/rust/cargo/bin:$PATH

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
