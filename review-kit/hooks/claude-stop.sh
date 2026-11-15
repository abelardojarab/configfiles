#!/bin/sh
# Claude Code Stop hook: before an agent ends its turn, run the review-kit
# code-quality sweep over what it changed (uncommitted and untracked files)
# and, on findings, refuse the stop so the agent fixes them first.
#
# Install in ~/.claude/settings.json (or a project's .claude/settings.json):
#   "hooks": {"Stop": [{"hooks": [{"type": "command",
#       "command": "sh \"$REVIEWKIT_HOME/hooks/claude-stop.sh\""}]}]}
#
# Acts only in a repository that opted in to the kit (reviewkit.home is set,
# as install.sh does), so other repositories and sessions are untouched.
# reviewkit.agentStop set to false turns it off for one repository.
#
# Exit codes, as Claude Code reads them: 0 lets the agent stop; 2 blocks the
# stop and feeds stderr back to the agent. When the agent is already
# continuing because of this hook (stop_hook_active), it lets it stop, so a
# finding the agent cannot fix never loops; the next turn checks again.
input=$(cat)
case $input in
    *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;;
esac
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
home=$(git config --get reviewkit.home 2>/dev/null) || exit 0
[ -n "$home" ] || exit 0
[ "$(git config --bool --get reviewkit.agentStop 2>/dev/null)" = false ] \
    && exit 0
kit=${REVIEWKIT_HOME:-$home}
[ -f "$kit/scripts/cq_sweep.py" ] || kit=$home
[ -f "$kit/scripts/cq_sweep.py" ] || exit 0
out=$(python3 "$kit/scripts/cq_sweep.py" --worktree --strict 2>&1)
code=$?
[ "$code" -eq 1 ] || exit 0
{
    echo "review-kit: the code-quality sweep found problems in the files you"
    echo "changed. Fix each one, or say in your reply why it does not apply,"
    echo "before finishing."
    echo
    printf '%s\n' "$out"
} >&2
exit 2
