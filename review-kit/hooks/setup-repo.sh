#!/bin/sh
# Sets a repository up for review-kit in one step: installs the git hooks
# (install.sh, which also records reviewkit.home, the switch the Claude
# Code Stop hook looks for) and writes AGENTS.md at the repository root
# from the kit's template, with <kit> replaced by the kit's path.
#
# Usage: setup-repo.sh [REPO_DIR]    (default: the current directory)
#
# An AGENTS.md that already exists is left alone: merge the kit's rules
# into it by hand. A CLAUDE.md or CLAUDE.local.md makes Claude Code read
# that file instead of AGENTS.md, so the script says so when it finds one.
#
# Exit codes: those of install.sh (0 done, 1 hook conflict or git failure,
# 2 bad arguments or not a git repository).
set -eu

if [ "$#" -gt 1 ]; then
    echo "usage: setup-repo.sh [REPO_DIR]" >&2
    exit 2
fi
repo=${1:-.}

here=$(cd "$(dirname "$0")" && pwd -P)
kit=$(dirname "$here")

sh "$here/install.sh" "$repo"
top=$(git -C "$repo" rev-parse --show-toplevel)

agents=$top/AGENTS.md
if [ -e "$agents" ]; then
    echo "left the existing $agents as it is; merge $kit/AGENTS.md into it"
else
    # Drop the template's note to the person copying it (the paragraph
    # that starts "Copy this file"), then fill in the kit's path.
    awk 'skip && /^$/ { skip = 0; next }
         /^Copy this file/ { skip = 1 }
         !skip' "$kit/AGENTS.md" | sed "s|<kit>|$kit|g" > "$agents"
    echo "wrote $agents"
fi

for name in CLAUDE.md CLAUDE.local.md; do
    if [ -e "$top/$name" ]; then
        echo "note: Claude Code reads $name instead of AGENTS.md here; add" \
             "a line to it such as \"Follow the rules in AGENTS.md\""
    fi
done
