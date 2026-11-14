#!/usr/bin/env python3
"""Stack churn: lines a commit removes that an earlier commit of its stack
added.

A later commit that deletes, moves or rewrites what an earlier commit of the
same stack added makes reviewers approve a state the stack then replaces. The
fix is to fold the later edit into the commit that introduced the lines
(`git commit --fixup` plus `git rebase -i --autosquash`), not to stack it.

Usage:
  stack_churn.py [--base B] [--limit N]

The stack is merge-base(B, HEAD)..HEAD, oldest first; B defaults to
reviewkit.base and N to reviewkit.churnLimit. A commit whose subject says
"pure move" or "golden" only relocates or regenerates lines, so later commits
may edit them without counting.

It sees only lines. A later commit that hides or re-parses an earlier one's
output without touching its lines is not listed: read the stack as one diff
for that.

Exit codes:
  0  no commit at or over the limit
  1  at least one commit at or over the limit
  2  the stack could not be read, contains a merge, or is empty
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

# A commit may extend a statement an earlier one added (one more argument or
# condition, often a wrapped call of 2-3 lines). From this many non-blank
# lines on, it is replacing what the earlier commits did.
LIMIT = 5
MOVE_ONLY = kit.MOVE_ONLY


class NotLinear(Exception):
    """The range holds a merge, so line numbers cannot be carried from one
    commit to the next."""


def read_stack(base_commit, head="HEAD"):
    """Reads the stack base_commit..head from git.

    Returns (order, titles, stack): the commits oldest first as 12-character
    hashes, {commit: subject}, and [(commit, git diff)] as churn() takes it.
    All three are empty when the range is empty. Raises kit.GitError when
    git fails and NotLinear when the range contains a merge commit.
    """
    merges = kit.merge_commits(base_commit, head)
    if merges:
        raise NotLinear("%s is a merge commit, so the stack %s..%s is not "
                        "one chain" % (merges[0][:12], base_commit[:12], head))
    order, titles, stack = [], {}, []
    for commit in kit.stack_commits(base_commit, head):
        short = commit[:12]
        order.append(short)
        titles[short] = kit.subject(kit.message(commit))
        stack.append((short, kit.commit_diff(commit)))
    return order, titles, stack


# The diff parser is shared with the other scripts.
sections = kit.sections


def apply(owned, hunks, change):
    """Carries {old line number: owning change} through one file's hunks.

    Returns ({new line number: owner}, [(owner, text)] of owned lines
    removed). Lines the hunks add are owned by `change`.
    """
    result, removed, seen, offsets = {}, [], set(), []
    for old_start, old_len, new_start, new_len, lines in hunks:
        # A zero-length side names the line before the hunk, not its first.
        old_no = old_start + (old_len == 0)
        new_no = new_start + (new_len == 0)
        for line in lines:
            if line.startswith("\\"):
                continue
            if line.startswith("-"):
                if old_no in owned:
                    removed.append((owned[old_no], line[1:]))
                seen.add(old_no)
                old_no += 1
            elif line.startswith("+"):
                result[new_no] = change
                new_no += 1
            else:
                if old_no in owned:
                    result[new_no] = owned[old_no]
                seen.add(old_no)
                old_no += 1
                new_no += 1
        offsets.append((old_no, new_no - old_no))
    for line_no, owner in owned.items():
        if line_no in seen:
            continue
        offset = 0
        for first_after, hunk_offset in offsets:
            if line_no < first_after:
                break
            offset = hunk_offset
        result[line_no + offset] = owner
    return result, removed


def churn(stack):
    """Finds the lines each change of a stack removes from an earlier one.

    stack: [(change, git diff of that change)], oldest first.
    Returns ({(earlier, later): [(path, text, moved)]}, {change: lines
    added}), counting non-blank lines only. `moved` is true when `later` adds
    the same text back (a move or a re-indent) instead of dropping or
    rewording it.
    """
    owners = collections.defaultdict(dict)
    pairs = collections.defaultdict(list)
    added = {}
    for change, diff in stack:
        files = list(sections(diff))
        plus = [line[1:].strip() for _, _, hunks in files for hunk in hunks
                for line in hunk[4] if line.startswith("+")]
        added[change] = sum(1 for text in plus if text)
        readded = set(plus)
        for old, new, hunks in files:
            owned = owners.pop(old, {}) if old else {}
            result, removed = apply(owned, hunks, change)
            if new:
                owners[new] = result
            for owner, text in removed:
                if text.strip():
                    pairs[(owner, change)].append(
                        (new or old, text.strip(), text.strip() in readded))
    return dict(pairs), added


def totals(pairs, titles):
    """{later change: lines it removes from earlier ones}, move-only earlier
    changes excluded."""
    counts = collections.Counter()
    for (earlier, later), lines in pairs.items():
        if not MOVE_ONLY.search(titles.get(earlier, "")):
            counts[later] += len(lines)
    return dict(counts)


def report(pairs, added, titles, order, limit=LIMIT, laters=None):
    """One block per change that removes lines of an earlier one, oldest
    first. `laters`, when given, keeps only the blocks of those changes."""
    counts = totals(pairs, titles)
    out = []
    for later in order:
        earlier_ones = [e for e in order if (e, later) in pairs]
        if not earlier_ones or (laters is not None and later not in laters):
            continue
        mark = "CHURN" if counts.get(later, 0) >= limit else "ok   "
        out.append("%s %s removes %d line(s) that earlier commits of this "
                   "stack added:" % (mark, later, counts.get(later, 0)))
        for earlier in earlier_ones:
            lines = pairs[(earlier, later)]
            moved = sum(1 for _, _, was_moved in lines if was_moved)
            exempt = (" [move-only commit, not counted]"
                      if MOVE_ONLY.search(titles.get(earlier, "")) else "")
            out.append("  %d of the %d that %s added (%d moved or "
                       "re-indented, %d dropped or reworded)%s"
                       % (len(lines), added.get(earlier, 0), earlier, moved,
                          len(lines) - moved, exempt))
            by_path = collections.defaultdict(list)
            for path, text, was_moved in lines:
                by_path[path].append(("moved   | " if was_moved
                                      else "dropped | ") + text[:110])
            for path, texts in by_path.items():
                out.append("    %s" % path)
                out += ["      %s" % text for text in texts[:6]]
                if len(texts) > 6:
                    out.append("      ... %d more" % (len(texts) - 6))
    return "\n".join(out)


def main(argv):
    parser = argparse.ArgumentParser(
        description="Lines a commit removes that an earlier commit of its "
                    "stack added.")
    parser.add_argument("--base",
                        help="mainline ref (default: reviewkit.base)")
    parser.add_argument("--limit", type=int,
                        help="churn limit (default: reviewkit.churnLimit)")
    args = parser.parse_args(argv)
    try:
        limit = (args.limit if args.limit is not None
                 else kit.config_int("churnLimit"))
        base_commit = kit.merge_base(kit.resolve_base(args.base))
        order, titles, stack = read_stack(base_commit)
    except (kit.KitError, NotLinear) as exc:
        print("stack_churn: not checked: %s" % exc)
        return 2
    if not order:
        print("stack_churn: no commits in %s..HEAD" % base_commit[:12])
        return 2
    pairs, added = churn(stack)
    for change in order:
        print("%s  +%-6d %s" % (change, added.get(change, 0),
                                titles[change][:90]))
    print(report(pairs, added, titles, order, limit)
          or "no commit removes a line an earlier commit of the stack added")
    counts = totals(pairs, titles)
    over = [c for c in order if counts.get(c, 0) >= limit]
    if over:
        print("\n%d commit(s) at or over %d lines (%s): fold each edit into "
              "the commit that introduced the lines (git commit --fixup "
              "<earlier>, then git rebase -i --autosquash), or re-cut the "
              "stack so every commit is a final state. Below the limit, "
              "check each listed line too." % (len(over), limit,
                                               ", ".join(over)))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
