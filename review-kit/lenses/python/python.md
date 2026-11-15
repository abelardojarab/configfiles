# Python Lens

What a reviewer checks on Python lines. Baseline:
https://google.github.io/styleguide/pyguide.html, or the guide the repository
names.

## 1. Docstrings and comments

- Docstring summary: one physical line, at most 80 characters
  (`scripts/cq_sweep.py` checks the length).
- Every function with non-obvious logic or over ~15 lines has a docstring
  that starts with a verb phrase and documents each return path, including
  `None` and raised exceptions.

## 2. Names and shape

- Module-private constants are `_CAPS_WITH_UNDER`; module-private functions
  start with an underscore.
- No single-character names or aliases outside `i`, `j`, `k`; no `as x`
  imports.
- No redundant parentheses around a single value when the line fits.
- Prefer a comprehension or a generator to a loop that only builds a list;
  prefer `dict.get` or `in` to a try/except around a lookup.

## 3. Imports

- Import modules, not names, unless the repository's convention differs; one
  import per line; standard library, third party and local in separate groups.
- Every import is used in the file. Never import for a side effect without a
  comment saying so.

## 4. Tests

- Test names describe everything the test verifies; one scenario per test.
- Build fixtures in the shapes the production loader produces; a fixture no
  loader can emit is a finding (`lenses/common/testing.md` §A).
- Assert specific fields, not whole dicts: `assert policy == base` breaks when
  a concurrent change adds a default. Filter excluded keys first:
  `rest = {k: v for k, v in policy.items() if k not in _IGNORED_KEYS}`.
- Precondition checks in builders raise `ValueError` inside the builder, not
  downstream.
