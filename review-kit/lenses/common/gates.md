# Push gates

Scope: every push that puts commits in front of a reviewer, and every rewrite
of a commit message that is already there. "Push now, fix after" is never
allowed, including for small or comment-only changes.

## 1. Run the gate; push only on exit 0

Gate and push a stack of changes as one group, never a single middle commit.
Pushing one commit alone leaves its descendants on a stale base in the review
tool and lets a parent's lint findings show up on its children.

From anywhere in the repository, with the stack checked out:

```
scripts/local_review.py     # only when an AI reviewer is configured
scripts/gate.py
git push
```

The `pre-push` hook refuses a push whose commits the gate has not passed in
their current form. The gate fails on any of:

* Tracked files that differ from `HEAD`: the linters would check something
  other than what is pushed.
* A commit message with authorship attribution to an AI or a tool, a
  duplicated paragraph, an empty subject, or a missing required trailer.
* A truth-audit flag (`scripts/truth_audit.py`): a named symbol that does not
  exist, a commit reference that does not exist or is unmerged and not called
  pending, a `knob = value` claim that is not in the tree, a duplicated
  paragraph.
* In protobuf projects: a `.proto` enum value the commit adds that the
  stack's non-test code uses nowhere, or only in `==`/`!=` comparisons and
  `case` labels: a dead enum value (`lenses/protobuf/protobuf.md`).
* A commit that removes 5 or more lines which earlier commits of its stack
  added (`scripts/stack_churn.py`; `lenses/common/stack_shape.md`): fold each edit
  into the commit that introduced the lines, or re-cut the stack.
* In C++: a read through a map's `operator[]`, which inserts on a miss, on a
  line the stack adds to non-test code: use `find()`, or `at()` where every key exists
  by construction. The gate also prints map lookups whose key does not change
  inside the enclosing loop: hoist each or say why not.
* A finding of a configured linter, and a finding of a configured static
  analyzer on a line the stack adds. Findings on untouched lines are printed
  as out of scope.
* With an AI reviewer configured: a commit without a clean local review. Any
  High or Medium finding that is neither fixed nor moved under `## Declined`
  with a reason blocks. So does a declined reason under 20 characters, or one
  that cites a `Class::member` found neither in the stack's code nor in the
  tree.

It also warns, without failing, on a commit over `reviewkit.maxLines`
changed lines (added plus deleted, 150 by default; 0 turns the warning off
for repositories that take large commits), unless its subject says pure move
or golden. 150 is a soft ceiling to stay under, not a hard limit: a
single-problem commit may go over it (`change_hygiene.md` §1). It also warns
on a commit whose message has more than `reviewkit.maxWords` words (150 by
default; 0 turns the warning off) above its first `<details>` block,
trailers excluded: cut what the diff already says and collapse evidence and
diagrams (`change_hygiene.md` §3).

Every failure is fixed, then the gate is re-run until it exits 0, except that
after 7 AI review rounds on one commit that still leave a High or Medium
finding open, the agent stops and asks the user (`AGENTS.md`, "Before
pushing"). Never pass `--no-verify` to get around a hook.

## 2. Never hand-write a local review

If `scripts/local_review.py` cannot run, fix the runner or stop and say so.
Never write, copy or summarize a report into the review directory by hand, and
a review done in the same session that wrote the code does not stand in for
one: it reviews its own assumptions. The gate rejects a report without the
runner's first line or under 400 characters.

A report is keyed by the commit's fingerprint (message body plus net patch
lines), so a rebase alone keeps it valid and any edit voids it.

## 3. Overriding a truth-audit flag

A flag that is a genuine false positive is overridden by one line in
`<state dir>/truth_overrides/<fingerprint>.txt`: the exact flag line, ` :: `,
and a reason of at least 20 characters. State the flag and the reason to the
person you are working for. The fingerprint in the file name voids the
override on any edit to the commit.

## 4. Every sentence is verified, not only the flagged ones

Exit 0 is necessary, not sufficient. The truth audit prints a checklist of
every comment line the diff adds and every line of the message. Before
pushing, verify each one against its proof (the code line, the config value in
the tree, the test, the commit it cites), recompute every number, and fix
anything that is not true in the tree and at this position in the stack. A
sentence that depends on unmerged work says "once <that change> lands".

## 5. Reviewer pass before pushing

Run `lenses/common/review_lens.md` on the final diff and message after the gate
passes. Answer each check in one line; a "no" gets fixed first, then the gate
is re-run.

## 6. No attribution

Never write authorship attribution to an AI or a tool into a commit message,
in any form: no "Generated with", no AI co-author trailer, no agent name. When
copying trailers from an existing message, drop any such line.

Exception: a project whose process asks for tool disclosure wins. In a Linux
kernel tree the changelog says which tools helped and how
(`lenses/kernel/kernel.md` §1), and the gate blocks only a `Signed-off-by`,
`Co-developed-by` or `Co-authored-by` that names an AI tool.

## 7. After pushing

Confirm the message in the review tool matches the local one, and that the
tool's own analyzers show nothing the local run missed. A finding that shows
up only after the push means a check was skipped or scoped wrongly: fix it,
re-run the gate and push again.
