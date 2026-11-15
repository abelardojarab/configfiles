# Protobuf Lens

What a reviewer checks when a change touches `.proto` files or the code that
reads them. Baseline: https://protobuf.dev/programming-guides/style/.

## 1. Schema changes stand alone

- Messages, fields, enum values and schema comments go in their own change,
  immediately below the code change that reads them, never mixed with code or
  configuration (`lenses/common/change_hygiene.md` §1).
- No dead fields, messages or enum values: never add one with no reader in
  the stack of changes or the frontend. `scripts/gate.py` blocks an added
  enum value that the stack's non-test code uses nowhere, or only in `==`/`!=`
  comparisons and `case` labels; such a value has no producer.
- A value that can be missing uses explicit presence and stays unset; never
  write `0.0` that reads as a measured zero.

## 2. Schema comments

- 3-6 lines per field or message, written for the config author: the
  high-level rule and a pointer to the code entry point for the formula.
  Never duplicate a formula across schema, code and description; three copies
  drift.
- An enum value's comment describes the branch that assigns it. When that
  branch moves or disappears, the comment changes in the same change.

## 3. File hygiene

- New messages use contiguous field numbers 1..N and carry `// Next ID: N+1`
  like their siblings (`scripts/cq_sweep.py` checks the comment).
- No issue references in schema comments except the tracking issue of a
  `TODO`.
- No unrelated edits: don't add or delete blank lines, reorder or reflow
  neighboring fields.

## 4. Enums in the reading code

- Exhaustive decision outcomes: every candidate in a multi-stage decision gets
  exactly one terminal outcome value; never `UNSPECIFIED`, never silently
  overwritten by a later stage (`lenses/common/design.md` §4).
- Never iterate an enum from `_MIN` to `_MAX` with integer casts; use the
  descriptor or a utility that enumerates declared values.
- One dispatcher per enum, with a `default:` that logs fatally in debug
  builds and the comment `// To add a strategy: add an enum value to the
  proto and a case here.` (`lenses/cpp/cpp.md` §3 for the C++ form).
- Adding the next enum value touches exactly the schema and one `case`.
  Touching a struct, comparator or second `switch` means the design is wrong.
