# Change Hygiene Lens

How a change (a commit or pull request) is cut, described, pushed and defended in review. Applies to every change, in any language.

The step order around pushing is in `lenses/common/gates.md`; the gate itself is
`scripts/gate.py`.

## 1. One problem per change

- Never solve more than one problem in a change. If the title or description
  needs "and" to join two checks, behaviors or fixes ("Add retry budget and
  timeout validation"), split it into two changes before writing code.
- Two independent checks in the same loop are still two changes, even when
  they share a function and a test builder. Bundling them lets feedback on one
  block the other, and a larger change takes more review rounds.
- Schema changes (messages, fields, enum values, schema comments) go in their
  own change, never mixed with code or configuration
  (`lenses/protobuf/protobuf.md` for protobuf schemas).
- A removal (a public function, a flag, a default, an overload, an
  accepted input) is the stated purpose of its own change, never a side
  effect of another. A removal callers can see is deprecated first where
  the project has a process for it, and the description says what replaces
  it and how to migrate.
- Aim to keep every change under 150 changed lines (added plus deleted,
  tests included, as `scripts/cq_sweep.py` counts them; a modified line
  counts twice). It is a soft ceiling, not a hard limit. Get under it by
  keeping the change tight (no speculative code, test scaffolding no larger
  than the logic, a pure refactor or a schema change in its own change), not
  by cutting one problem in half. Going over it is a prompt to ask "is this
  one problem?", not an automatic split: split when the size comes from a
  second problem, never where the halves would break `stack_shape.md` §1 or
  leave a helper with no user, and say in the reply why a single-problem
  change stays whole. Well past ~200 lines a split is expected, except for a
  pure move or a generated or golden-file update, which say so in the first
  line of the description.
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
  read-only, `<` vs. `>=`, with an epsilon on float boundaries.
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
  A project whose process asks for disclosure wins (`lenses/kernel/kernel.md`).
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
- A change to code on a hot path (a kernel, an inner loop, an allocator, a
  serialization path) shows before and after numbers from the same
  benchmark, inputs and machine, each run more than once, even when the
  change is not meant to change speed. A slowdown in a cleanup is a finding.
- Add a flow diagram (at most 12 lines, in a fenced block) when the change reads
  more than one input or sits in the middle of a pipeline: inputs, this change,
  outcome, each box naming the real file or function.
- End the description of every change that alters runtime behavior,
  production configuration, monitoring (queries, alerts, dashboards) or a
  binary's inputs with a production impact table, collapsed where the review
  tool renders HTML:

      <details>

      <summary>Production impact</summary>

      | Dimension | Details |
      | :--- | :--- |
      | Blast radius | ... |
      | Rollout | ... |
      | Monitoring / watch | ... |
      | Rollback | ... |

      </details>

  - Blast radius: the files, binaries and environments the change reaches,
    and what it leaves unchanged (a flag off by default, alternatives only
    added to a pattern).
  - Rollout: one entry per binary or config that ships the change, with the
    file that defines its stages. Say in bold when something pushes
    everywhere at once with no canary.
  - Monitoring / watch: the metric, log or table to check after it lands,
    filtered to production, and the alerts that must stay at zero.
  - Rollback: the revert command plus any state a revert does not undo
    (records written, capacity moved, traffic already served) and what to do
    first.
  - A test-only or doc-only change writes one line instead:
    "Production impact: none (<why>)."
  - Check every cell like any other sentence: rollout stages come from the
    file that defines them, not from memory.
  - `scripts/gate.py` warns when a commit adds, changes or deletes a file
    matching `reviewkit.impactPaths` and has neither form.
- Show the result where the user sees it. A change that reaches a UI (a
  dashboard, a web page, a rendered table) includes a screenshot of the new
  or changed view, captured from a local or test server running the change,
  with one line saying what it shows. A change that reaches a CLI or a log
  includes the relevant output excerpt in a fenced block (at most 15 lines)
  or a link to it, produced by running the change. Put either in a
  collapsed `Screenshot` or `Example output` block where the review tool
  renders HTML. A backend-only or schema-only change that nothing renders
  yet says which later change of the stack shows it.
- No internal process targets in descriptions. Don't cite the line-count
  ceiling, gate names, local review reports or other workflow targets as
  the reason for a split or a design ("keeps each change under 150 lines").
  Give the reviewer-facing reason instead: one problem per change, can be
  rolled back on its own, a layer boundary.
- Name the precedent in the description: write
  `Precedent: <change> (<file>)` for the closest precedent the pattern scan
  found (`lenses/common/pattern_scan.md`), or
  `Precedent: none (<what the scan searched>)` when it found none.
- A change that only adds a schema, an option that a later change of the
  same stack reads, or a switch that stays off until a later change turns
  it on says "no behavior changes with this change alone" and why it is
  split ("so it can be rolled back on its own"). A configuration change
  that turns something on does change behavior and does not use this
  wording; an option with no reader in the stack stays out (`design.md`
  §1).
- A trailer that tells CI an output difference or a skipped check is
  intended states what changed and how it was checked (the diff reviewed,
  the command run), never a bare value.

## 4. Pre-push

- Push a stack of changes as a group. Whenever any change in it is edited,
  including a parent or middle change, run formatting, tests and the gate over
  the whole range and push it in one command. Pushing one change alone leaves
  its children on a stale base and lets the parent's findings show up on them.
- Run the repository's formatter over the stack, then its dependency cleanup
  tool on every touched build target, then the full listed test set.
- For guard tests, re-run the negative check on the final code
  (`testing.md` §B).
- Push only when the configured static analyzer (`reviewkit.tidyCmd`) reports
  nothing on the change's lines and `scripts/truth_audit.py` has no
  unexplained flags, with every checklist sentence verified, the description
  included.
- If a parent merges mid-stack and the group push fails, sync, re-run the gate
  on what is left, push it, and reword "the parent change" to the merged change.
- In a repository that uses jj: target change IDs, not commit IDs; edit on top
  and squash rather than rewriting in place; abandon stale commits in one
  call. This avoids divergent changes. Before editing a workspace another
  agent may hold, check the operation log for recent operations and ask the
  user to stop that agent.

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
