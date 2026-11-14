#!/bin/sh
# Installs the review-kit hooks (pre-commit, commit-msg, pre-push) into a
# repository and records the kit's location in its git config.
#
# Usage: install.sh [REPO_DIR]    (default: the current directory)
#
# Hooks go to `git rev-parse --git-path hooks`, which honors core.hooksPath.
# A hook that exists and was not installed by this script (it lacks the line
# "# review-kit hook") is left alone and the install stops.
#
# Exit codes: 0 installed, 1 a foreign hook is in the way or git failed,
# 2 bad arguments or not a git repository.
set -eu

marker='# review-kit hook'

if [ "$#" -gt 1 ]; then
    echo "usage: install.sh [REPO_DIR]" >&2
    exit 2
fi
repo=${1:-.}

here=$(cd "$(dirname "$0")" && pwd -P)
kit=$(dirname "$here")

if ! top=$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null); then
    echo "install.sh: $repo is not inside a git work tree" >&2
    exit 2
fi
hooks=$(git -C "$top" rev-parse --git-path hooks)
case $hooks in
    /*) ;;
    *) hooks=$top/$hooks ;;
esac

# Check every hook before changing anything, so a refusal leaves the
# repository as it was.
for name in pre-commit commit-msg pre-push; do
    target=$hooks/$name
    if [ -e "$target" ] && ! grep -qxF "$marker" "$target"; then
        echo "install.sh: $target exists and was not installed by" \
             "review-kit; move it away or merge it by hand, then re-run" >&2
        exit 1
    fi
done

mkdir -p "$hooks"
for name in pre-commit commit-msg pre-push; do
    cp "$here/$name" "$hooks/$name.review-kit-tmp"
    chmod +x "$hooks/$name.review-kit-tmp"
    mv -f "$hooks/$name.review-kit-tmp" "$hooks/$name"
    echo "installed $hooks/$name"
done
git -C "$top" config reviewkit.home "$kit"
echo "set reviewkit.home = $kit in $top"
