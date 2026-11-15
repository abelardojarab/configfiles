# Change Hygiene

How a change (a commit or pull request) is cut, described, pushed and defended in review.

The step order around pushing is in `rules/gates.md`; the gate itself is
`scripts/gate.py`.

## 1. One problem per change

- Never solve more than one problem in a change. If the title or description
  needs "and" to join two checks, behaviors or fixes ("Add retry budget and
  timeout validation"), split it into two changes before writing code.
- Two independent checks in the same loop are still two changes, even when
  they share a function and a test builder. Bundling them lets feedback on one
  block the other, and a larger change takes more review rounds.
- Schema changes (`.proto` messages, fields, enum values, schema comments) go
  in their own change, never mixed with code or configuration.
- Keep every change under 150 changed lines (added plus deleted, tests
  included, as `scripts/cq_sweep.py` counts them). A modified line counts
  twice. Over 150 means split before pushing, not explain in the description.
  The only exceptions are a pure move and a generated or golden-file update,
  and those say so in the first line of the description.
- Cut a feature into these slices:
  1. A schema-only change (the schema plus 3-6 line comments for config
     authors).
  2. A pure move or no-behavior refactor.
  3. One change per check, gate or policy rule, each with only the tests that
     fail when that check is deleted.
  4. A wiring change (call sites, metrics, decision records) with the
     end-to-end tests that need the full wiring.
  5. A configuration or dark-launch change, separate from code and schema.
- A guard test change may expose a shared helper it needs; tests for that
  helper are a separate change.
- Stack shape comes first (`stack_shape.md`): each change is a final state that
  no later change of the stack undoes.

## 2. Truthful comments and descriptions

- Before sending for review and before every "Done" reply, re-read every
  comment, docstring, schema comment, doc and description sentence against the
  final code at the top of the stack of changes.
- Describe only what this change implements. Never document a later change's
  mechanism as present, and never add a check or end-to-end test for a gap that
  only opens in a later change of the stack.
- State what changed relative to the parent change. A change that replaces or
  removes something its unmerged parent added is folded into the parent instead
  (`stack_shape.md` §1). If that is impossible (the parent merged or is
  approved and merging), say so explicitly in the description.
- Behavior that exists only in someone else's pending change is written as
  "pending change N ... once it lands", never in the present tense. Check the
  change's state yourself; never inherit an issue's framing as current behavior.
- Guards and validators state (a) what the check guarantees, (b) which adjacent
  check it does not make hold and why, (c) the state at head today ("no
  violations", or the count and the entries covering them).
- Failure messages and descriptions are written for the person who hits them
  (the config author, the on-call engineer), not for the reviewer.
- Be precise: exact sets (which states are included), resource amounts vs.
  instance counts, intended vs. currently observed values, read-write vs.
  read-only, `<` vs. `>=` (`cpp.md` §1).
- Verify reviewer-suggested wording like your own. Before applying a sentence
  a reviewer or a bot proposes, re-derive each qualifier from the code; a
  suggestion often drops a condition its own evidence states.

## 3. Description mechanics

- List every test actually run. Touching a shared library means querying its
  reverse dependencies and running and listing all of them. Follow the
  directory's convention for how the list is written.
- Rewriting a description never drops trailers: read the current one first and
  carry over reviewers, issue references and merge settings verbatim.
- Merge edits made in the code review tool (by reviewers or bots) into the local
  description before pushing again; a push replaces the remote description.
- Reviewer changes go to both places in the same step: the code review tool and
  the local commit trailers, or the next push adds removed reviewers back.
- The author is always listed as a reviewer of his own change and reviews it
  before anyone else sees it.
- Trailers go at the bottom. No AI or tool attribution in any form: no
  "Generated with", no "Co-authored-by" naming an agent, no agent names.
- If the review tool can merge a change once it is approved and checks pass,
  enable that on every change; a change that must not land says so explicitly.
  Enabling it is not sending for review: send for review only when asked.
- Don't edit the description while a pre-merge check is running if the tool
  cancels the run on edit; the change then sits approved but unmerged.
- A trailer that closes an issue on merge is only for an issue with no open
  work left. Use a plain reference while follow-up work remains.
- Write change and issue references bare, not in code formatting, so the tool
  links them.
- Back runtime claims with production data. If the description says what
  production did or does (a value, an assignment, a failure reason, a timeline):
  - Link the metrics-system or database query that shows it, pinned to the
    incident window and filtered to the exact entity and the production job
    (staging and production often export the same metrics; an unfiltered count
    mixes them).
  - Attach a screenshot of the graph or the query output.
  - Add a 2-4 sentence reading: what each series is, the before and after
    values, when they changed and which change caused it, and how that matches
    the recorded error.
  - Run the query yourself before citing its numbers, or say whose reading
    it is.
- Add a flow diagram (at most 12 lines, in a fenced block) when the change reads
  more than one input or sits in the middle of a pipeline: inputs, this change,
  outcome, each box naming the real file or function.

## 4. Pre-push

- Push a stack of changes as a group. Whenever any change in it is edited,
  including a parent or middle change, run formatting, tests and the gate over
  the whole range and push it in one command. Pushing one change alone leaves
  its children on a stale base and lets the parent's findings show up on them.
- Run the repository's formatter over the stack, then its dependency cleanup
  tool on every touched build target, then the full listed test set.
- For guard tests, re-run the negative check on the final code
  (`testing.md` §B).
- Push only when the configured static analyzer (clang-tidy for C++) reports
  nothing on the change's lines and `scripts/truth_audit.py` has no
  unexplained flags, with every checklist sentence verified, the description
  included.
- If a parent merges mid-stack and the group push fails, sync, re-run the gate
  on what is left, push it, and reword "the parent change" to the merged change.
- jj: target change IDs, not commit IDs; edit on top and squash rather than
  rewriting in place; abandon stale commits in one call. This avoids divergent
  changes.
- Before editing a workspace another agent may hold, check the operation log
  for recent operations and ask the user to stop that agent.

## 5. Post-push

- Static analysis in the review tool is asynchronous: results read right after a
  push may belong to the previous revision. Wait for a result timestamped after
  the push, then check again before replying "Done" or adding reviewers.
- Resolve every static-analysis and sync-guard finding before publishing
  replies.
- Call out unrelated test failures with evidence: show from the dependency
  graph that the failing target depends on nothing the change touched.

## 6. Review replies

- Address the comment in code, in the change that introduced that code
  (`stack_shape.md` §1), and push before replying.
- Keep replies short and concrete: what changed, where the proof is, what was
  deliberately not done and why. Leave the thread for the reviewer to resolve
  unless they asked otherwise.
- An optional suggestion you decline gets an explicit sentence, not silence.
- When a reviewer suggests one fix and then asks a follow-up question ("also,
  should this return an error?"), the question is a question. Answer it with the
  trade-off (blast radius, the file's precedent), say which of the two the code
  now does and why. Never adopt the follow-up because it sounds stricter and
  silently drop the first suggestion. Before changing an assertion or
  error-handling kind in a reply, read the same file's other "impossible"
  branches and match them (`pattern_scan.md` §1).
