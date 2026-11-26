# Testing Lens

What a reviewer checks in tests, by test kind; classify the test before applying any rule, because the kinds have opposite shapes.

| Kind | Thing under test | Typical location |
|---|---|---|
| A. Unit tests | the code | `*_test.*` or `test_*.*` next to the library |
| B. Production-config conformance guards | the production configuration | a test directory that reads the checked-in production config files |
| C. Config-language tests | values written in the config language | tests next to the config sources |

Applying §A to a §B test is the most common way to produce a test file a
reviewer asks to shrink.

## A. Unit tests

- Use concise spec structs and builders (`OrderSpec`, `BuildOrderBook`), not
  large hand-written protobuf payloads in test bodies. Every field of a spec
  struct is set to a non-default value by at least one test in the same change;
  otherwise delete the field and pass the value in the builder.
- Deletion test for every test: each test must fail when the production code
  added in that change is deleted. No end-to-end test that still passes with
  the new check removed (because a later stage repairs the state) or that only
  duplicates a unit test while adding dependencies; put it in the wiring change
  where removing the check fails it.
- Run the mutation check, don't reason about it: delete or invert each new
  check one at a time, run the tests, confirm at least one fails, restore.
  Record the result in the description ("Mutation: removing the stock check
  fails `RejectsOrderAboveStock`"). A check is every early return, special case,
  clamp (`max(0.0, ...)`) and floor inside a new function, not only the
  whole gate. A branch whose deletion leaves every test green is redundant
  (delete it) or needs a test that tells the two paths apart.
- A bug fix comes with a regression test that reproduces the bug: run it
  before the fix and see it fail for the reported reason, then after the fix
  and see it pass. The description names the test and the failure it showed
  before the fix. A fix without such a test says why none can be written.
- No default-valued assertions: an expected value equal to the field's default
  (0, 0.0, false, "", enum value 0) still passes when the setter is deleted.
  Pick inputs that give a non-default value, or assert presence.
- Line coverage of the diff: every line the change adds to non-test code runs in
  its tests. An uncovered line needs a test or a one-line reason in the
  description (logging only, a debug-only assertion, error pass-through). Coverage proves the
  test reaches the line, the mutation check proves it asserts on it, neither
  proves production reaches it (`design.md` §2).
- Build inputs only in shapes the upstream stage produces in production. Never
  set flags in tests that upstream never emits.
- Config fixtures follow the rules of the generator that produces real configs,
  and the fixture comment names that generator. No fixture the generator could
  not emit (duplicate keys it would reject, a reference to an entity the parent
  does not list).
- A check dropped as redundant needs a test of what makes it redundant: add a
  test in which only the remaining mechanism produces the expected outcome, and
  mutate the mechanism to see it fail.
- No duplicated helpers across test files in one directory; shared fixtures go
  in a test utilities header. Two short config readers in guard tests are the
  exception (§B).
- Focused tests: 15-40 lines, one scenario each, a 1-2 line rationale comment
  above the test, short IDs (`"o1"`, `"u1"`), no external numbering prefixes.
- Boundary tests: both sides of every threshold (`x < t` and `x >= t`),
  including IEEE-754 cases at exact rational boundaries (`2 - 1.8 = 0.2`).
- A check that can run alone is tested alone, both ways. When configuration
  picks which checks run (either one, or both), each check that can run
  alone needs, in the mode where it does, one case where it keeps the item
  and one where it drops it, and the mutation "this check always passes"
  must fail a test in every such mode. A suite whose only single-check case
  passes the item stays green when that check does nothing.
- Exclusion tests flip the outcome: when testing that an entity is excluded from
  a sum, choose numbers where the result is below the threshold with the
  exclusion and would cross it without.
- Precedence tests: when outcome A beats B, trigger both and assert A.
- Empty and zero-state tests: empty inputs, zero candidates, all data missing,
  empty records and zeroed gauges without crashing.
- Refactor rule: extracting or generalizing shared code leaves the
  unchanged mode's tests passing with zero edits; otherwise split the behavior
  change into its own change or justify it in the description.
- Helper behavior is tested next to the helper, never in a §B guard that
  calls it.

## B. Production-config conformance guards

These run before merge to keep the production configuration consistent. The
code is glue.

- One test over the production configs, with a body of about 15-40 lines: read
  with the directory's existing reader idiom (copying two short readers is
  acceptable; consolidating them is a separate change), join with shared helper
  functions, assert the rule. No spec structs, builders, allowlists or
  synthetic scenarios in the guard file.
- Logic with branches goes in a helper with synthetic tests. Before writing the
  guard, find where comparable logic lives in its directory and how it is
  tested. If the computation has any filter, skip, join, override or fallback
  beyond a plain lookup, put it in a helper function with synthetic tests for
  every branch, including branches production config doesn't exercise (an
  override of 0, a read-only entry, a value over the limit). Then the guard
  calls the helper and asserts. Split it into two changes: helper with its
  tests, then the thin guard. A branch only production config runs can be wrong
  and stay green.
- Keys may be a plain pair or a concatenated string; the named-key-struct rule
  of the language lens (`lenses/cpp/cpp.md` §4) does not apply here.
- Share join keys and normalizers from the helper library; never re-type a
  default value or copy the helper.
- Vacuity guard: assert that the joined data is non-empty, not only the
  inputs.
- The failure message is for the config author: one assertion per violating
  entity, stating the entity, why it is a problem, how to fix it and the
  tracking issue.
- The negative check is the proof: temporarily break a real config, run the
  test, paste the exact failure line into the description, revert, and confirm
  the diff shows only intended files. Re-run it on the final revision after any
  refactor of the test.
- Set precision: if the config holds entities in several states (enabled,
  dry run, disabled), say "any entity, whatever its state" unless the code
  filters on state; never "launched".
- Skips mirror production exactly: every filter names the production predicate
  it mirrors and applies it at the production granularity. If production
  decides per group, collect the group set first and skip every member of it;
  never skip per member.
- Diagnostic run before pushing: temporarily instrument the guard (counts per
  filter, broken down by kind; entities excluded or joined unexpectedly), run
  it on production config, then restore the file byte for byte (`cmp` against a
  saved copy). Root-cause every unexpected entity in code before pushing
  (`review_lens.md`); never write it into the description as a known quirk.

## C. Config-language tests

- Stay within the column limit; split long labels across adjacent string
  literals.
- No whole-dict assertions (`assert policy == base` breaks when a concurrent
  change adds a default). Assert specific fields, or filter excluded keys first:
  `rest = {k: v for k, v in policy.items() if k not in _IGNORED_KEYS}`.
- Fail early in builders: precondition checks raise `ValueError` inside the
  builder, not downstream.
- Negative sweeps: every dark-launch or override test loops over all
  environments and asserts the feature is on only for its targets and never
  leaks into others.
- A builder that fans keyword arguments out to several callees classifies every
  callee parameter as shared, single-callee only, or callee-dependent. Anything
  with a callee-dependent default or a single-callee assertion is not
  shareable: route it to the one callee it belongs to, or assert it is absent
  until a per-callee override exists. Test the rejection.
