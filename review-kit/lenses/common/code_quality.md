# Code-Quality Checks

Yes/no checks on the diff that reviewers otherwise raise as nits; run them before every push, review request and "Done" reply.

Run them through `scripts/cq_sweep.py`, then read the diff for what the script
cannot see. Goal: zero code-quality comments.

## 0. Baseline

- C++: https://google.github.io/styleguide/cppguide.html and
  https://abseil.io/tips/.
- Protobuf: https://protobuf.dev/programming-guides/style/.
- Python: https://google.github.io/styleguide/pyguide.html.
- TypeScript: https://google.github.io/styleguide/tsguide.html.
- Where a rule here is stricter than the guide (braces on every body, §7), this
  rule wins. Read the guide's section for any construct you are unsure of
  before writing it.

## 1. Docs and comments the change made stale

- Concept sweep, not just the hunk: for every symbol, enum value, knob or mode
  the change adds, renames or removes, search the whole package (docs, schema
  comments, header and definition comments, test comments, the description) for
  statements about it and about its siblings. A new mode makes neighboring
  sentences wrong ("No effect when the cap is unset", a heading that no longer
  covers a new row).
- Header and definition comments move together: when one changes, re-read the
  other.
- Comments name real parameters. After a rename, search for the old name in
  comments.
- No line numbers in docs or comments; use symbol names.
- Recount every count or total a doc states ("17 knobs", "four metrics").
- Locations are exact: name the file that defines a function, not one that
  calls it.
- Ordering and phase words are exact ("before step 2 of `Plan`", not "early").
- Test comments state the test's actual numbers.
- Absolutes hold on every path: a sentence with "every", "always", "never",
  "only" or "fail closed" is checked against early returns. Where two stated
  rules cover the same case, say which wins.
- Field comments match the producer: name every case the producer leaves the
  field absent, zero, negative or fail-closed.
- Resolved threads stay true: after a rewrite, re-check every thread answered
  "Done".
- Outcome sentences say which entity gets which value.

## 2. Function comments

- Every non-obvious function has a comment, including file-private ones. A
  name that hides an allowlist needs one.
- Start with a verb phrase ("Returns ...") and check every pronoun's antecedent.
- Document every return path: each `std::nullopt`, each propagated error, what
  negative or non-finite input does, and preconditions checked in callees.
- Declaration comments say what the function does and how to call it;
  definition comments say how it works. No history about deleted code.
- Pure arithmetic helpers in headers are `constexpr`, with full parameter names.
- Non-obvious reducers get a why (`Sum()` where one element is expected, `Max()`
  across a dimension).

## 3. Includes and build dependencies

- For every include in a touched file, name a symbol from it used in that file.
  None: delete it and its build dependency.
- Include the header for what you newly use, even if it arrives transitively,
  in test files too (`<cstdint>`, `<tuple>`, `<utility>`, the generated
  `.pb.h`). clang-tidy's include cleaner is the authority (it flags `<compare>`
  as unused for a defaulted `operator<=>`). Never touch includes for code the
  change didn't touch.
- For every build dependency of a touched target, name a header from it that
  the target includes. None: delete it.
- After removing code, re-check its includes.

## 4. Protobuf hygiene

- New messages use contiguous field numbers 1..N and carry `// Next ID: N+1`
  like their siblings.
- No issue references in code comments except the tracking issue of a `TODO`.
- No unrelated edits: don't add or delete blank lines, reorder or reflow
  neighboring fields.
- A value that can be missing uses explicit presence and stays unset; never
  write `0.0` that reads as a measured zero.

## 5. Python

- Docstring summary: one physical line, at most 80 characters.
- Every function with non-obvious logic or over ~15 lines has a docstring.
- Module-private constants are `_CAPS_WITH_UNDER`.
- No single-character names or aliases outside `i`, `j`, `k`.
- No redundant parentheses around a single value when the line fits.

## 6. Tests

- Test names describe everything the test verifies. Adding assertions to a test
  means renaming it or writing a new test.
- No leftover names from earlier revisions of the change.
- Names and lines stay within 80 columns; shorten the name if needed.
- `ASSERT_THAT(x, SizeIs(n))` before indexing `x[0]`.
- Test every new overload or parameter in the change that adds it, with an
  argument that differs from the old default.
- Bind a value-returning lookup once per iteration; never call it twice in one
  assertion.
- Golden files match their siblings' format exactly.

## 7. Small C++ style

- Braces on every `if`/`for` body, including one-line `continue;`.
- Constant arrays and lookup tables live at namespace scope in the anonymous
  namespace, not function-local (Abseil tip #140).
- Name magic numbers that appear more than once (`kMicrosPerSecond`).
- A function past ~60 lines, or with a second job, gets the new part extracted.
- Match a sibling loop's guards.
- A "keep these lists in sync" comment becomes a machine-checked sync guard if
  the repository has one, where the code cannot be shared. A guard that ties a
  text format to a parser in another layer is a design finding
  (`stack_shape.md` §2).
- Hoist a map lookup whose key doesn't change out of the loop; don't follow
  `contains()` with `[]` on the same key. Don't hoist a reference into a map the
  loop inserts into: a rehash invalidates it.
- Wrap a value in `std::optional(value)`, not `std::make_optional(value)`, when
  the other branch of a ternary is `std::nullopt`.

## 8. Log lines

- Don't append a separator after a prefix helper that already ends with one.
- A decision log keeps the numbers that justify the decision, in every mode.

## 9. TypeScript

- No redundant type assertions.
- Don't export a function only so a test can reach it; test the public API.
- Use `??` and explicit null checks instead of `Number(x) || 0`.
- Helper functions use verb names and declare return types.
