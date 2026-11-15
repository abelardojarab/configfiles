# Instructions for coding agents

Copy this file into a repository as `AGENTS.md` (or the name your agent
reads), and replace `<kit>` with the absolute path of this directory.

## Before writing code

1. Read `<kit>/lenses/common/pattern_scan.md` and post the pattern-scan
   note it asks for. No code before that note exists.
2. Read the lenses that match the work. A lens is a reviewer's checklist for
   one concern; the common ones apply to every change, a language lens only
   when the diff touches that language. All are under `<kit>/lenses/`:

- Every change: `common/change_hygiene.md`, `common/stack_shape.md`,
  `common/design.md`, `common/code_quality.md`
- Tests: `common/testing.md`
- C: `c/c.md`
- C++: `cpp/cpp.md`
- CUDA (`.cu`, `.cuh`): `cpp/cpp.md` and `cuda/cuda.md`
- Go: `go/go.md`
- Linux kernel tree: `c/c.md` and `kernel/kernel.md`
- Protobuf schemas or their readers: `protobuf/protobuf.md`
- Python: `python/python.md`
- TypeScript: `typescript/typescript.md`
- Before every push: `common/gates.md`, `common/review_lens.md`

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
- Verify every sentence of the checklist the truth audit prints, then run
  the two checklists in `<kit>/lenses/common/review_lens.md` on the final
  diff and answer each check in one line in your reply.

## Small changes

A change is small when it is one commit of at most 20 changed lines that
adds no branch, function, test, file or dependency: a typo, a comment, doc
wording, a version or configuration value, a rename within one file. For
a small change:

- The pattern-scan note is one line: the closest precedent and why the
  change follows it.
- Read `<kit>/lenses/common/change_hygiene.md` and the lens of the
  language the diff touches, not the whole list.
- After the truth audit, say in one line which checks of
  `<kit>/lenses/common/review_lens.md` apply, instead of answering
  each.

Everything else stays: `cq_sweep.py`, the AI review, the gate, the commit
message rules. When the change outgrows these limits, or the reviewer or
the gate flags anything, switch to the full path.

## Commit messages

- Say why the change exists, what it does not do, and how it was tested.
- No authorship attribution to an AI or a tool, in any form, unless the
  project's process asks for disclosure (a Linux kernel tree does: see
  `<kit>/lenses/kernel/kernel.md`). An agent never adds a
  `Signed-off-by`.
