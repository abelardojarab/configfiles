# Code-Quality Lens

Yes/no checks on the diff that reviewers otherwise raise as nits; run them before every push, review request and "Done" reply.

Run them through `scripts/cq_sweep.py`, then read the diff for what the script
cannot see. Goal: zero code-quality comments. The language lenses
(`lenses/c`, `lenses/cpp`, `lenses/protobuf`, `lenses/python`,
`lenses/typescript`) add the checks that only make sense in one language.

## 0. Baseline

- Follow the style guide the repository names. Absent one, the language lens
  names a default guide.
- Where a lens is stricter than the guide (braces on every body), the lens
  wins. Read the guide's section for any construct you are unsure of before
  writing it.

## 1. Docs and comments the change made stale

- Concept sweep, not just the hunk: for every symbol, enum value, knob or mode
  the change adds, renames or removes, search the whole package (docs, schema
  comments, header and definition comments, test comments, the description) for
  statements about it and about its siblings. A new mode makes neighboring
  sentences wrong ("No effect when the cap is unset", a heading that no longer
  covers a new row).
- Declaration and definition comments move together: when one changes, re-read
  the other.
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
- Document every return path: each absent value, each propagated error, what
  negative or non-finite input does, and preconditions checked in callees.
- Declaration comments say what the function does and how to call it;
  definition comments say how it works. No history about deleted code.
- Non-obvious reducers get a why (`Sum()` where one element is expected, `Max()`
  across a dimension).

## 3. Imports, includes and build dependencies

- For every import or include in a touched file, name a symbol from it used in
  that file. None: delete it and its build dependency.
- Import what you newly use, even if it arrives transitively, in test files
  too. Never touch imports for code the change didn't touch.
- For every build dependency of a touched target, name a file from it that the
  target uses. None: delete it.
- After removing code, re-check its imports.

## 4. Naming and shape

- Full words, never single-letter names or abbreviations (`cfg`, `res`, `val`)
  outside loop indices and type parameters. When a loop converts a spec into a
  built object, name them `item_spec` and `item`.
- Name magic numbers that appear more than once.
- A function past ~60 lines, or with a second job, gets the new part extracted.
- Match a sibling loop's guards.
- A "keep these lists in sync" comment becomes shared code, or a machine-checked
  sync guard if the repository has one. A guard that ties a text format to a
  parser in another layer is a design finding (`stack_shape.md` §2).
- Hoist a lookup whose key doesn't change out of the loop; don't follow a
  membership test with a second lookup on the same key.
- Lines stay within the repository's column limit (`reviewkit.maxCols`,
  80 by default).

## 5. Tests

- Test names describe everything the test verifies. Adding assertions to a test
  means renaming it or writing a new test.
- No leftover names from earlier revisions of the change.
- Assert a collection's size before indexing into it.
- Test every new overload or parameter in the change that adds it, with an
  argument that differs from the old default.
- Bind a value-returning lookup once per iteration; never call it twice in one
  assertion.
- Golden files match their siblings' format exactly.

## 6. Log lines

- Don't append a separator after a prefix helper that already ends with one.
- A decision log keeps the numbers that justify the decision, in every mode.
