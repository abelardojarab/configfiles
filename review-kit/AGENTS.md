# Instructions for coding agents

Copy this file into a repository as `AGENTS.md` (or the name your agent
reads), and replace `<kit>` with the absolute path of this directory.

## Before writing code

1. Read `<kit>/rules/pattern_scan.md` and post the pattern-scan note it asks
   for. No code before that note exists.
2. Read the rule files that match the work:

| When | Read |
|---|---|
| Every change | `rules/change_hygiene.md`, `rules/stack_shape.md`, `rules/design.md`, `rules/code_quality.md` |
| C++ | `rules/cpp.md` |
| Tests | `rules/testing.md` |
| Before every push | `rules/gates.md`, `rules/review_lens.md` |

Where a rule conflicts with the repository's own contributor rules or an
explicit reviewer comment, those win. If two rules still conflict, say so
instead of picking one silently.

## While writing code

- One problem per commit, under 150 changed lines, each commit a final state
  that no later commit of the stack undoes.
- Run `<kit>/scripts/cq_sweep.py` on each commit and fix what it prints.

## Before pushing

```
<kit>/scripts/local_review.py   # only when an AI reviewer is configured
<kit>/scripts/gate.py
```

- Push only when the gate exits 0, and only when asked to.
- Never pass `--no-verify`. Never write a review report or a gate stamp by
  hand.
- Verify every sentence of the checklist the truth audit prints, then run the
  two checklists in `rules/review_lens.md` on the final diff and answer each
  check in one line in your reply.

## Commit messages

- Say why the change exists, what it does not do, and how it was tested.
- No authorship attribution to an AI or a tool, in any form.
