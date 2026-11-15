# Stack Shape

How to cut work into a stack of changes, checked before splitting and before every push of a stack.

A change should be one self-contained change, small enough to review and not
so small that its implications are hard to understand
(https://google.github.io/eng-practices/review/developer/small-cls.html). The
size limit and slice list in `change_hygiene.md` §1 apply inside these rules.
Every change being under 150 lines does not make a stack reviewable: reviewers
read it as a whole and reject one whose changes replace each other.

## 1. Every change is a final state

- No change undoes an earlier change of its stack. Nothing an unmerged change
  adds (code, a test, an output format, help text, a comment, a sync-guard
  block) is deleted, moved, hidden, reformatted or reworded by a later change of
  the same stack. Otherwise each change is small, but reviewers approve states
  the next change replaces.
- Cut the stack from the finished design, not from the order the work
  happened. Settle the whole change first, then cut it so each change adds its
  piece in the form that piece has at the top of the stack. The pattern scan
  note (`pattern_scan.md` §2) says what each planned change leaves final.
- A change to what an unmerged change introduced goes into that change. Review
  feedback, a new requirement or a later idea that changes an earlier change's
  output is edited on top and squashed into it, then the children are
  re-tested. It is never a new change on top.
- A later change may extend a statement an earlier change added (one more
  argument, condition or column), and may edit code a parent only moved (the
  parent's first description line says pure move).
- Before every stack push, run `scripts/stack_churn.py` over the stack. It
  lists each line a change removes that an earlier change of the stack added.
  Exit 1 means a change removes 5 or more such lines: fold or re-cut before
  pushing. The gate runs the same check (`rules/gates.md`) and blocks such a
  change. Below 5, look at each listed line.
- The script only sees lines, so also read the stack as one diff (from the
  bottom change's parent to the top change). A change that hides or re-parses
  an earlier change's output without touching its lines shows up only there.
- Small and final together. If the only cut under 150 lines leaves a state a
  later change replaces, cut along a layer (§3) or a complete feature instead.
  If no cut gives both, keep the final-state cut, stop, and tell the user the
  change is over the limit and why.

## 2. One layer decides; the others display

- The layer that owns the data makes every decision and has the tests. For a
  report produced by a backend and shown by a web frontend, the backend decides
  what each table entry shows (marker, icon, hover text) and the frontend
  renders what it is given. One definition of a term such as "paused", in one
  language.
- Never rebuild a decision from another layer's display text: no
  `text.includes('(paused: ')`, no regex over a marker, no
  `header.split(' ')[0]`, no join on keys cut out of rendered text. When the
  text changes, the feature disappears and nothing fails.
- A value that is structured where it is produced is never printed into a
  string and parsed back (two booleans rendered as `"read+write"` and matched
  with `/\bread\b/`).
- A sync guard that ties a text format to its parser is a design finding, not
  a safeguard: move the decision to one side.

## 3. Split at the layer boundary

- A feature that crosses layers starts with the change that makes the boundary
  carry the data generically: shared code or stubs that isolate changes between
  layers. Nothing in that change names the feature. Its round-trip tests are its
  first user and the next change of the stack is its production user, so it is
  not dead surface (`design.md` §1). Example: per-entry hover text that the CSV
  encoder emits for any table, the frontend parser reads, and the renderer
  shows as a tooltip.
- Then one change per feature, each on one side of the boundary and each a
  final state.
- The standalone schema change of `change_hygiene.md` §1 is the same cut,
  between schema and code.

## 4. Sending a stack for review

- Send a change for review when it is unlikely to undergo significant further
  changes, and hold child changes until the parent is relatively stable.
- When asked to send a stack whose bottom change carries a design the
  reviewers have not seen (a new channel, format or split), say so and propose
  sending that change and the first change that uses it, with the rest pushed
  but not sent. The user decides.
