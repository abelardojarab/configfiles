# Design Lens

What a reviewer checks in the design of production code: what to expose, which branches may exist, where formulas and decisions live, and what to record. Language-neutral; the language lenses give the concrete forms.

## 1. Surface minimization

- No premature or single-caller exposure: a function or struct with one caller,
  or whose other callers live in later changes, stays file-private (anonymous
  namespace or equivalent).
- No single-use intermediate structs or pre-build loops over tiny collections.
  When a group has at most ~10 members, don't define local structs and a
  40-line loop that pre-builds them to feed one helper; write a ~25-line helper
  that reads the existing accessors directly, and compute one-line values
  inline at the call site.
- Exposing a canonical join key, limit helper or normalizer from a file-private
  scope to a shared low-level header removes a duplicate. That is the
  single-formula case of §3, not a violation of this rule.
- No dead fields, schema messages or enum values. Schema changes live in their
  own change immediately below the code change that reads them; never add a
  field or enum value with no reader in the stack of changes or the frontend
  (`lenses/protobuf/protobuf.md`).
- No zero-entry escape hatches: an allowlist, ignore list, optional parameter,
  default argument or `Default*()` returning an empty set is a dead mechanism.
  The first real exception adds it, with a reason and a `TODO(owner)`.
- One way to do each thing in a public API: no alias for an existing name,
  no overload or extra accepted type that only saves the caller a
  conversion, no implicit default that hides a choice, no convenience hook.
  Convenience alone does not justify new public surface; a new entry point
  says in the description why the existing one is not enough.
- No test-only public methods on core classes; verify through observable
  outputs or keep internals private.
- Scaffolding is proportional to the logic it exercises. If the test file is
  longer than the code it guards, cut it.

## 2. Reachability

- Upstream reachability: before reading an input field in a downstream stage,
  verify how the upstream stage populates it in production. Never write a check
  or a synthetic test for an input shape that upstream overwrites or never sets.
- Stack-stage reachability: if a gap in a guarantee only opens when a later
  change alters behavior, put the guard and its end-to-end test in that later
  change, never in an earlier one where the existing code still repairs the
  state.
- In-process reachability: for every `if`, default-on-absent read, `case`,
  `default` or defensive check, ask whether it can run given what upstream already
  established. If an earlier step already classified the entity (say, as
  "missing reading"), a later step must not re-check the same condition.
- Input validation is upstream too: don't write or test branches for input
  shapes that an input validator already rejects.
- Reachable is not needed: for every early return or special case, ask what the
  general path returns on the same input. If it returns the same on every input
  upstream allows (trace the callers' gates), delete the branch. A reachability
  proof shows a branch fires, not that it changes anything.
- Configuration can gate behavior at more than one level (for example a global
  enable flag and a per-entity setting). Check every level before describing
  when the behavior happens.
- Purely defensive code against impossible state becomes a debug-only
  assertion (only when the guarantee is non-obvious) or is deleted. Never
  business-logic branches for impossible input. Exception: inside a per-item
  loop where the item has an outcome to record, log loudly (fatal in debug
  builds), record the outcome and continue, never return an error for the
  whole run (`lenses/cpp/cpp.md` §5 for the C++ form).
- A `case` whose whole body is a fatal-in-debug log plus a fallback is a dead
  branch (`lenses/cpp/cpp.md` §3).
- Write a production-reachability proof for every behavior change. Test
  coverage does not show reachability: a unit test that sets a field directly
  covers a branch production never takes. For each new branch, gate or input
  field read, add one line to the description under `Prod reachability:` -
  `<branch>: fires when <field>=<value>, set by <upstream code | config path>`.
  Verify the value in the production config or upstream code, not from memory.
  If no such line can be written, the branch is dead at this point in the
  stack: delete it or move it to the change that makes it reachable. A
  dark-launch flag counts only if the description names where it is (or will
  be) enabled.

## 3. One canonical formula, ordering and dispatch

- One copy of any domain formula, comparator or dispatch table per concept. A
  second candidate struct plus comparator that re-derives score-then-identity
  is a duplicate even if the keys differ.
- A file-private copy still counts as existing: expose it from the header (its
  comment travels with it) and call it from both sides; never re-type it in a
  test or caller. Parameterize an existing helper (`GetRateLimits(policy,
  current_load)`) so callers reuse its edge-case logic ("0 means no limit")
  instead of restating it inline.
- Behavior implemented twice (a CPU reference and a GPU kernel, a Python
  library and its C++ core, two language clients) changes in both in the
  same stack. If one side cannot change yet, the description names it and
  the test that will catch the two drifting apart.
- Build-graph layering: the code under test never depends on the code that
  checks its output (validators, conformance checks). Put shared limit and math
  helpers in a low-level target both already depend on. If B needs a symbol
  from A and A already depends on B, extract a lower leaf target both depend
  on: never copy, never invert the edge.
- No public caching types for cheap lookups in small, immutable, in-memory
  stores; a second lookup is fine.
- Parse once, before the per-item loop: convert a repeated field into a local
  set or map once per entity, then iterate. Never call a helper that re-parses
  the list for every item. A local set is not the caching type the previous
  bullet forbids.
- No O(N^2) sibling scans: precompute group totals in a first pass so each
  member evaluation computes the remaining sibling slack in O(1).
- Pass existing data down instead of querying again.

## 4. Architecture

- Measurement vs. policy: measurement utilities are pure, stateless math with
  no knowledge of the decisions made from them. Thresholds, caps, ordering,
  budgets and eligibility live in the policy layer.
- Passive data objects never send RPCs or do heavy work; active objects drive
  the flow. Keep dynamic state and static topology in separate structs.
- No calculator, provider or factory layers and no catch-all utils. Use the
  repository's configuration system, not command-line flags, for configuration.
- Fail explicitly instead of silently skipping. A skip that is safe gets a
  comment saying why.
- Exhaustive decision outcomes: every candidate in a multi-stage decision gets
  exactly one terminal outcome enum value; never `UNSPECIFIED`, never silently
  overwritten by a later stage. Where two outcomes can apply, the doc says which
  wins.
- An outcome names the limit that binds. Where more than one cap, budget or
  guard can stop the same item, give the item the label of the limit that would
  still stop it with the others lifted. For each label ask: "with only this
  limit raised, would the item go through?" A "no" puts the item under another
  label. Derive the condition from what the label means, not from the order the
  checks happen to run in, and check again after a rename. The label's doc
  states the counterfactual, two identical items get the same label whatever
  their rank, and a test has one item hitting both limits. Otherwise metrics
  overstate what raising one limit would achieve.

## 5. Observability

- Any new or changed metric adds rows to the metrics documentation in the same
  change: name, fields, type, units, whether it is summable across a field.
- Bounded cardinality: metric fields are small closed sets (environment, mode,
  enum names). Never per-instance names, raw job IDs or unaggregated strings
  without explicit team approval.
- Reset gauges at the start of each run so stale entities don't linger.
- Decision-record messages are annotated `// Observability only`, grouped by
  topic with section headers, and populated by one `FillXxx` helper per topic
  that writes into an output message.

## 6. Principles that hold in any system

Each of these came from a review finding; they are written here as the
general rule, not the incident.

- Check a hard validator's exact inequality before mutating state, sharing the
  validator's canonical helper, and only in the change where later stages can
  no longer undo the mutation. Size allowances from the state at the start of
  the run and subtract what earlier steps of the same run already used. No
  stateful reservations that later stages must undo.
- Test a new threshold algebraically at its boundary case (the smallest
  configuration it applies to) and against a live snapshot before adding it.
  A share or ratio sums only the entities that actually share the resource.
- One member missing data never disqualifies its whole group: scope the
  "missing" outcome to that member, let it contribute zero to sums, and keep
  it in denominators so ratios cannot inflate.
- An operation that takes effect immediately must be proven against capacity
  that exists now, not capacity a later step may add.
- Compare a float sum against a boundary with an epsilon (`1.0 - 1e-9`) so
  exact rational sums don't fail on IEEE-754 rounding.
- A requested knob in an issue is a hypothesis: check it in code and data
  before applying it.
