# C Lens

What a reviewer checks on C lines. Baseline: the repository's style guide,
else https://google.github.io/styleguide/cppguide.html where it applies to C.

## 1. Comments

- Headers: 1-3 factual lines per function: what it does, caller
  preconditions, ownership of every pointer passed in or returned. No
  motivation essays.
- Implementations explain why, never restate syntax; blocks of 5-10 lines at
  most.
- Every function comment starts with a verb phrase and documents each return
  path: every error code, every `NULL`, what a negative or overflowing input
  does.

## 2. Shape

- Braces on every `if`/`for`/`while` body, including a one-line `continue;`.
- Constant arrays and lookup tables are `static const` at file scope, not
  function-local.
- Name magic numbers that appear more than once; one `#define` or `enum` per
  concept, next to its siblings.
- Full words, never `m`, `c`, `s`, `v`, `e`, `cfg`, `res`, `val`; `i`, `j`,
  `k` only as integer indices.
- A function past ~60 lines, or with a second job, gets the new part
  extracted.
- A read-only lookup in a table never writes a default on a miss.

## 3. Includes

- Include the header for every symbol used, even one that arrives
  transitively: `<stdint.h>` for fixed-width integers, `<stdbool.h>` for
  `bool`, `<stddef.h>` for `size_t` (`scripts/cq_sweep.py` checks the
  fixed-width case in headers).
- For every include in a touched file, name a symbol from it used in that
  file. None: delete it.

## 4. Errors and logging

- Every error path returns a distinct code or sets a distinct status that the
  caller can act on; never a bare `-1` where callers need to tell cases apart.
- Size the failure to the branch: inside a per-item loop, a state that "can't
  happen" whose only effect is skipping that item logs, records the item's
  outcome and continues; it does not abort the run.
- At most one informational log per committed mutation; loops log start and
  end with the item count, items at verbose level.
