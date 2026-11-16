# code-server with the tools this setup needs baked in, instead of
# installed at every start: python3 (with venv and headers) for
# review-kit's git hooks and projects; GCC, LLVM/Clang 23 (18 for Mull),
# build tools, debuggers and analyzers; lcov and gcovr for coverage
# reports; Go, Rust and Bazel; gRPC and
# protobuf tools (protoc and its plugins, grpcurl, buf); Mull and mutmut
# for mutation testing; the Docker CLI for the host's socket; kubectl
# for the host's Kubernetes cluster, with helm and k9s; Node and uv
# for the MCP servers in the chat's mcp.json; ruff for Python linting
# and formatting; jj for Jujutsu repositories
# and the editor's jj extensions; gh for GitHub; gcloud for Google Cloud
# and Gemini Code Assist; Claude Code and the Gemini CLI; and everyday
# command-line tools, nvtop among them.
#
# Every download that is not from Ubuntu's archive is pinned and checked
# against its published SHA-256 (Docker's and LLVM's apt keys, against
# their published fingerprints; Google Cloud's, against the fingerprint
# of the key that signs its repository, since Google publishes none).
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
      cppcheck shellcheck lcov gcovr \
      protobuf-compiler libprotobuf-dev libgrpc++-dev protobuf-compiler-grpc \
      git-lfs ripgrep fd-find tree file zip unzip zstd rsync wget \
      sqlite3 htop nvtop tmux vim bc yq \
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

# kubectl from dl.k8s.io, at the cluster's version (v1.28.15) so the
# client stays within the supported skew. The kubeconfig is the host's,
# mounted read-only by docker-compose.yml.
ARG KUBECTL_VERSION=v1.28.15
ARG KUBECTL_SUM=1f7651ad0b50ef4561aa82e77f3ad06599b5e6b0b2a5fb6c4f474d95a77e41c5
RUN curl -fsSL -o /tmp/kubectl \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && echo "${KUBECTL_SUM}  /tmp/kubectl" | sha256sum -c - \
 && install -m 0755 /tmp/kubectl /usr/local/bin/kubectl \
 && rm -f /tmp/kubectl

# helm and k9s for the same cluster, through the same kubeconfig. helm
# stays on 3.x, the host's major version (helm 4 changed plugins).
ARG HELM_TGZ=https://get.helm.sh/helm-v3.22.1-linux-amd64.tar.gz
ARG HELM_SUM=896cf63684a42a723d61c980369d6e588330927deb13676ca0d85006dd6da0ea
ARG K9S_URL=https://github.com/derailed/k9s/releases/download
ARG K9S_TGZ=v0.51.0/k9s_Linux_amd64.tar.gz
ARG K9S_SUM=c3752ad51a5a4015a113819c4eeb6e55a4d0e4b8e652494797532f6fc8161dd7
RUN cd /tmp \
 && curl -fsSL -o helm.tgz "${HELM_TGZ}" \
 && curl -fsSL -o k9s.tgz "${K9S_URL}/${K9S_TGZ}" \
 && printf '%s  %s\n' "${HELM_SUM}" helm.tgz \
      "${K9S_SUM}" k9s.tgz | sha256sum -c - \
 && tar -C /usr/local/bin -xzf helm.tgz --strip-components=1 \
      linux-amd64/helm \
 && tar -C /usr/local/bin -xzf k9s.tgz k9s \
 && rm -f helm.tgz k9s.tgz

# jj (Jujutsu) from its GitHub release, the static musl build, for the
# editor's jj extensions (jjk, VisualJJ), which run it.
ARG JJ_URL=https://github.com/jj-vcs/jj/releases/download
ARG JJ_TGZ=v0.46.0/jj-v0.46.0-x86_64-unknown-linux-musl.tar.gz
ARG JJ_SUM=fce0271158e665ceb82dc66c5eb95b1728649094e9133074f3b5baece345fc08
RUN curl -fsSL -o /tmp/jj.tgz "${JJ_URL}/${JJ_TGZ}" \
 && echo "${JJ_SUM}  /tmp/jj.tgz" | sha256sum -c - \
 && tar -C /usr/local/bin -xzf /tmp/jj.tgz ./jj \
 && rm -f /tmp/jj.tgz

# gh, the GitHub CLI, from its GitHub release. It signs in with
# `gh auth login`, which keeps the token in ~/.config/gh on /config.
ARG GH_URL=https://github.com/cli/cli/releases/download
ARG GH_TGZ=v2.103.3/gh_2.103.3_linux_amd64.tar.gz
ARG GH_SUM=4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d
RUN curl -fsSL -o /tmp/gh.tgz "${GH_URL}/${GH_TGZ}" \
 && echo "${GH_SUM}  /tmp/gh.tgz" | sha256sum -c - \
 && tar -C /usr/local/bin -xzf /tmp/gh.tgz --strip-components=2 \
      gh_2.103.3_linux_amd64/bin/gh \
 && rm -f /tmp/gh.tgz

# gcloud, the Google Cloud CLI, from Google's apt repository, for Gemini
# Code Assist's project and application-default credentials. The key must
# match the fingerprint of the key that signs the repository before it is
# trusted. gcloud keeps its sign-in in ~/.config/gcloud on /config.
ARG GCLOUD_KEY_FPR=35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      -o /tmp/gcloud.asc \
 && gpg --show-keys --with-colons /tmp/gcloud.asc \
      | grep -q "^fpr:::::::::${GCLOUD_KEY_FPR}:" \
 && mv /tmp/gcloud.asc /etc/apt/keyrings/gcloud.asc \
 && echo "deb [signed-by=/etc/apt/keyrings/gcloud.asc]" \
      "https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y google-cloud-cli \
 && rm -rf /var/lib/apt/lists/*

# Claude Code, the native binary from Anthropic's release bucket, at the
# host's version, checked against the SHA-256 in that release's
# manifest.json. A rebuild with a new pin updates it, so the
# self-updater, which cannot write to /usr/local/bin, is off. It signs
# in with /login and keeps the token in ~/.claude/.credentials.json and
# its settings in ~/.claude.json, both on /config.
ARG CLAUDE_GCS=https://storage.googleapis.com
ARG CLAUDE_BUCKET=claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819
ARG CLAUDE_URL=${CLAUDE_GCS}/${CLAUDE_BUCKET}/claude-code-releases
ARG CLAUDE_VERSION=2.1.325
ARG CLAUDE_SUM=0dc4f4a9a165fc60746d7ae8489712e5fc352f1e7ad4eb22e7141bd0812eb0cf
ENV DISABLE_AUTOUPDATER=1
RUN curl -fsSL -o /tmp/claude \
      "${CLAUDE_URL}/${CLAUDE_VERSION}/linux-x64/claude" \
 && echo "${CLAUDE_SUM}  /tmp/claude" | sha256sum -c - \
 && install -m 0755 /tmp/claude /usr/local/bin/claude \
 && rm -f /tmp/claude

# Gemini CLI, the bundle from its GitHub release, at the host's version,
# checked against the SHA-256 GitHub publishes for the asset. It runs on
# the Node linked into /usr/local/bin below. It signs in through Google
# and keeps the token in ~/.gemini/oauth_creds.json on /config.
ARG GEMINI_URL=https://github.com/google-gemini/gemini-cli/releases/download
ARG GEMINI_ZIP=v0.64.0/gemini-cli-bundle.zip
ARG GEMINI_SUM=9d4ad33d15dcf35098919c69eb9d98b6dc640567f141d6fc4f8f053c8cbd8dae
RUN curl -fsSL -o /tmp/gemini.zip "${GEMINI_URL}/${GEMINI_ZIP}" \
 && echo "${GEMINI_SUM}  /tmp/gemini.zip" | sha256sum -c - \
 && unzip -q /tmp/gemini.zip -d /opt/gemini-cli \
 && ln -s /opt/gemini-cli/gemini.js /usr/local/bin/gemini \
 && rm -f /tmp/gemini.zip

# LLVM 23, the current stable branch, from apt.llvm.org, as the default
# clang, clangd, clang-format, clang-tidy, lld and lldb (linked into
# /usr/local/bin, ahead of Ubuntu's 18 in /usr/bin; a tool missing from
# the packages fails the build rather than leave a dangling link). The
# repository is trusted only after its key matches LLVM's published
# fingerprint.
# Ubuntu's LLVM 18 stays installed as clang-18 and friends: Mull's plugin
# is built for it, and Mull has no build for LLVM 23.
ARG LLVM=23
ARG LLVM_KEY_FPR=6084F3CF814B57C1CF12EFD515CF4D18AF4F7421
RUN curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key -o /tmp/llvm.asc \
 && gpg --show-keys --with-colons /tmp/llvm.asc \
      | grep -q "^fpr:::::::::${LLVM_KEY_FPR}:" \
 && mv /tmp/llvm.asc /etc/apt/keyrings/llvm.asc \
 && . /etc/os-release \
 && echo "deb [signed-by=/etc/apt/keyrings/llvm.asc]" \
      "https://apt.llvm.org/${VERSION_CODENAME}/" \
      "llvm-toolchain-${VERSION_CODENAME}-${LLVM} main" \
      > /etc/apt/sources.list.d/llvm.list \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      clang-${LLVM} clangd-${LLVM} clang-format-${LLVM} \
      clang-tidy-${LLVM} clang-tools-${LLVM} lld-${LLVM} lldb-${LLVM} \
      llvm-${LLVM} libclang-rt-${LLVM}-dev \
 && rm -rf /var/lib/apt/lists/* \
 && for tool in clang clang++ clangd clang-format clang-tidy \
      run-clang-tidy clang-apply-replacements ld.lld lld lldb lldb-dap \
      llvm-config llvm-symbolizer llvm-cov llvm-profdata llvm-objdump; do \
      src="/usr/bin/${tool}-${LLVM}"; \
      [ -e "$src" ] || { echo "missing $src"; exit 1; }; \
      ln -sf "$src" "/usr/local/bin/${tool}"; \
    done

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
# The CUDA toolkit (nvcc, ncu, nsys, compute-sanitizer, cuda-gdb) is the
# host's, mounted at /usr/local/cuda by docker-compose.yml; last on PATH,
# so a tool in the mount never shadows one of the same name in the image.
ENV PATH=/opt/rust/cargo/bin:$PATH:/usr/local/cuda/bin

# Ubuntu's Node is 18, too old for the MCP servers; nodejs-wheel brings a
# current one. A venv keeps these out of the system Python, and only the
# tools are linked onto PATH: putting the venv itself first would shadow
# python3 and pip with a root-owned venv the editor user cannot install
# into.
RUN python3 -m venv /opt/tools \
 && /opt/tools/bin/pip install --no-cache-dir uv nodejs-wheel mutmut \
      ruff==0.17.3 \
 && for tool in node npm npx uv uvx mutmut ruff; do \
      ln -s "/opt/tools/bin/$tool" "/usr/local/bin/$tool"; \
    done
