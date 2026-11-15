# Instructions for coding agents

Copy this file into a repository as `AGENTS.md` (or the name your agent
reads), and replace `<kit>` with the absolute path of this directory.

## Before writing code

1. Read `<kit>/lenses/common/pattern_scan.md` and post the pattern-scan note
   it asks for. No code before that note exists.
2. Read the lenses that match the work. A lens is a reviewer's checklist for
   one concern; the common ones apply to every change, a language lens only
   when the diff touches that language:

| When | Read |
|---|---|
| Every change | `lenses/common/change_hygiene.md`, `lenses/common/stack_shape.md`, `lenses/common/design.md`, `lenses/common/code_quality.md` |
| Tests | `lenses/common/testing.md` |
| C | `lenses/c/c.md` |
| C++ | `lenses/cpp/cpp.md` |
| CUDA (`.cu`, `.cuh`) | `lenses/cpp/cpp.md` and `lenses/cuda/cuda.md` |
| Go | `lenses/go/go.md` |
| Linux kernel tree | `lenses/c/c.md` and `lenses/kernel/kernel.md` |
| Protobuf schemas or their readers | `lenses/protobuf/protobuf.md` |
| Python | `lenses/python/python.md` |
| TypeScript | `lenses/typescript/typescript.md` |
| Before every push | `lenses/common/gates.md`, `lenses/common/review_lens.md` |

Where a lens conflicts with the repository's own contributor rules or an
explicit reviewer comment, those win. If two lenses still conflict, say so
instead of picking one silently.

## While writing code

- One problem per commit, under `reviewkit.maxLines` changed lines (150
  unless the repository sets otherwise), each commit a final state that no
  later commit of the stack undoes.
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
  two checklists in `lenses/common/review_lens.md` on the final diff and answer each
  check in one line in your reply.

## Commit messages

- Say why the change exists, what it does not do, and how it was tested.
- No authorship attribution to an AI or a tool, in any form, unless the
  project's process asks for disclosure (a Linux kernel tree does: see
  `lenses/kernel/kernel.md`). An agent never adds a `Signed-off-by`.
