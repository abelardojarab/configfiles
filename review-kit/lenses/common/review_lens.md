# Review Lenses

Two checklists to run on the final diff and description after the gate passes, then the review passes to run before pushing.

Answer each item in one line in the reply to the user. A "no" gets fixed first.

## Senior reviewer lens

This reviewer challenges suboptimal choices, separates fact from inference,
keeps things simple, researches first and agrees on the solution before code.

1. Challenge the approach. Name the simpler or more standard alternative (an
   existing helper, a config change instead of code, a smaller scope, a
   different layer) and say why this change beats it. If the reason isn't
   obvious from the code, one sentence goes in the description.
2. Why, not what. Every comment and description sentence states intent, a
   constraint or a trade-off. Delete any that only restate the code.
3. Fact vs. inference. Every claim about system behavior (production
   reachability, upstream inputs, config values, what a validator does) is
   backed by evidence you looked at: a code line, a config value at head, a
   test, a change's state, a query. Inferred claims are verified now or worded
   as assumptions.
4. No assumed context. If behavior depends on something you haven't read (an
   upstream caller, a config default, another change in flight), read it or
   ask. A guess found in review costs a round.
5. Keep it simple. Smallest change that solves the one problem: no speculative
   parameters, no new abstraction with one caller, no struct or loop that exists
   only to feed one function, no special case the general path already handles,
   no test scaffolding larger than the logic.
6. Research first. Search the repository for an existing helper, pattern or
   formula before writing one, and follow it. If you deviate from the local
   pattern, say why.
7. Agree before coding. For urgent or design-changing work, the approach (where
   the code lives, why it fires in production, how it splits into changes) was
   posted on the issue and acknowledged before the code was written. If not,
   tell the user before pushing.
8. High standard. Lint, format, dependency cleanup and local clang-tidy are
   clean (`scripts/gate.py` checks this).
9. Final states, one deciding layer (`stack_shape.md`). Read the stack of
   changes as one diff. No change deletes, moves, hides or re-parses what an earlier
   unmerged change added (`scripts/stack_churn.py` exits 0 and each line it
   lists is an extension), and no decision is made in two layers.

## Independent reviewer lens

This reviewer runs general code review and readability passes with no context
from the author, and finds bugs the author's own pass misses.

1. Same predicate as production. Every include, exclude or skip decision names
   the production function that makes the same decision and either calls it or
   mirrors it term by term, including every alternative (`a` non-empty or
   `source == AUTO`). A check written from the field name alone is a "no".
2. Same granularity as production. For each config field the diff reads, state
   which entity owns it in production (parent, child, member) and which code
   enforces that. If production decides per group, the diff decides per group:
   collect the group set first, then apply it to every member.
3. Every kind walked. Where a group has members of several kinds, trace the
   diff's logic separately for each kind and each sibling. If any kind takes a
   different path from the primary one, explain why production does the same,
   or fix it.
4. Branches production config doesn't exercise. A guard test runs only on
   production config, so a branch it never hits can be wrong and stay green.
   Name the production entry that exercises each branch. Any branch that is
   real logic belongs in a helper with synthetic tests, in this stack, not a
   follow-up (`testing.md` §B).
5. Anomalies are root-caused, never documented away. Any unexpected entity a
   diagnostic run turns up is traced to its cause in code before it is written
   into a comment or the description as scope. "It's within limits today" is
   not a cause.
6. Comments and scope match the code. After any logic change, re-read the
   test's doc comment, the failure message and the description's scope
   paragraph against the final code.
7. Moved header helpers pass a readability review in their new home: pure
   arithmetic helpers are `constexpr`, parameters have full domain names
   matching sibling declarations, and the comment is rewritten for the new
   callers (exact return value, no history of deleted code).
8. Function comments start with a verb phrase, have an explicit antecedent for
   every pronoun, and state preconditions enforced by callees before
   early-return paths.
9. New overloads and parameters are tested in the change that adds them, with
   an argument that differs from the old default so a version that ignored it
   fails.
10. Test include hygiene: include `<tuple>` and `<utility>` directly in test
    files, and never call a value-returning lookup twice in one assertion;
    bind it once per iteration.
11. Items 1-2 apply to sentences too. A sentence that says when something
    happens, or where two components differ, names the production predicate at
    every level (a global enable and a per-entity setting) and checks every
    combination.

## Review passes

Run these report-only on the local change before pushing
(`scripts/local_review.py` runs the automated ones); fix every finding or state why it doesn't apply, then
re-run the gate.

- On every change: removed behavior, cross-file ripple, tests.
- API compatibility: schema fields, status codes, error messages.
- Errors and retries; deadlines, only for a new or changed RPC.
- State and encapsulation.
- Resource bounds: loops, fan-out, quota.
- Logging and observability.
- Release and rollout: configuration and flags.
- Test blast radius: shared test helpers and fixtures.
- Includes and forward declarations.
- Performance: redundant map lookups or ones whose key does not change in
  the loop, missing `reserve`, ordered containers where hashing suffices,
  string `operator+` in loops, `string_view` parameters, protobuf messages
  built in loops.
- Readability against the language's style guide.
- A risk assessment of the change's production impact.
- For urgent or design-heavy changes, a first-principles review of the
  assumptions behind the approach.
