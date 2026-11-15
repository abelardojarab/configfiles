# C++ Lens

What a reviewer checks on C++ lines, in production code and its tests: comments, compile-time checks, enum dispatch, signatures, logging, defensive code, includes and small style.

Precedence across lenses: the more specific scope wins (a production-config
guard rule beats a generic test rule); an explicit reviewer comment on the
change beats any lens; if two still conflict, say so in the reply instead of
picking one silently. Baseline: the C++ style guide
(https://google.github.io/styleguide/cppguide.html) and the Abseil tips
(https://abseil.io/tips/); the `absl::` forms below apply where the project
uses Abseil, and their standard-library equivalents otherwise. Where the
repository wraps the standard logging and status macros, use its wrappers on
every line you add, even where the rest of the file does not.

## 1. Comments

- Schema comments are covered by `lenses/protobuf/protobuf.md` §2.
- Headers: 1-3 factual lines: what it does, caller preconditions, usage contract
  (for example, whether a limit helper is symmetric and leaves floors to another
  check). No motivation essays or derivations.
- Implementations: explain why, never restate syntax; blocks of 5-10 lines at
  most. Guard and predicate comments: 1-3 lines stating the condition that
  must hold.
- Moving a helper to a shared header: keep the source file clean (its local
  constants stay file-private), and audit the moved function as new code:
  - Mark pure arithmetic functions `constexpr` instead of `inline`.
  - Use full domain parameter names (`current_load`, not `current`) matching
    sibling declarations.
  - Rewrite the comment for the header's callers: start with a verb phrase
    ("Returns ..."), state the exact contract ("base allowance" rather than
    "maximum allowed" when a validator adds tolerances on top), delete history
    about deleted code paths.
- Every function comment starts with a verb phrase, has an explicit antecedent
  for every pronoun, and documents preconditions checked in callees that run
  before early-return paths.
- Precision: resource amounts vs. instance counts, intended vs. observed values,
  read-write vs. read-only, exact inequalities (`<` vs. `>=`, with a `1e-9`
  epsilon on float boundaries where exact rational sums can round down),
  fail-closed vs. record-and-proceed.

## 2. Compile-time verification and templates

- Closed enum domains and trait tables: `constexpr` arrays plus `static_assert`
  over `std::make_index_sequence<N>()`; never defer completeness to runtime
  tests.
- Generic code over user structs: require `std::is_aggregate_v<T>` and unpack
  with structured bindings so a field add or reorder fails to compile. No tuple
  indexing.
- Wrap dependent parameters in `std::type_identity_t<T>` so callers can pass
  `{}` or `std::nullopt`.
- Any constructor or method that stores a pointer or reference to a
  caller-owned object annotates the parameter `ABSL_ATTRIBUTE_LIFETIME_BOUND`
  and deletes the rvalue overload (`Bind(const Deps&&) = delete;`).
- Never iterate a protobuf enum from `_MIN` to `_MAX` with `int` casts; use the
  enum descriptor or a utility that enumerates declared values.

## 3. Enum dispatch

- Closed C++ `enum class`: exhaustive `switch` without `default:` so `-Wswitch`
  fires; `LOG(DFATAL)` after the switch.
- Protobuf enums: `default:` with `LOG(DFATAL)` and the comment
  `// To add a strategy: add an enum value to the proto and a case here.`
- One dispatcher per enum. The `switch` is the single mapping from enum to
  behavior, and every `case` returns that strategy's real result. A `case`
  whose body is only `LOG(DFATAL)` plus a fallback means the mapping leaked
  into a parallel comparator or struct: fold it back.
- Extensibility test: adding the next enum value touches exactly the schema and
  one `case`. Touching a struct, comparator or second `switch` means the design
  is wrong.
- Ranking tuples carry strategy-agnostic slots; unused slots stay `0`; never a
  second score struct per mode. Quantize every float sort key like its
  siblings (`std::llround`); never mix raw `double` and `int64_t` keys.

## 4. Class design and signatures

- Strategy hierarchies use the non-virtual interface pattern: public methods
  are non-virtual, validate shared preconditions (arity, non-empty spans,
  `std::isfinite`), then call a private pure-virtual method. Subclasses never
  repeat the checks.
- Every raw pointer in parameters, returns and members is `absl_nonnull` or
  `absl_nullable`.
- One-shot builders end with `Build() &&`. Use `absl::FunctionRef` for
  non-owning synchronous callbacks and `absl::AnyInvocable` for stored ones.
- Option structs bundle two or more optional tuning parameters, with defaults
  that preserve identity behavior, only for knobs that already have callers
  varying them. A knob with no caller is dead surface (`design.md` §1).
- Callers never read raw `*_override` fields; use an accessor that resolves
  the override, and say so on the raw getter.
- Accessors take the narrowest key (an enum), not an object that could belong
  to a different parent.
- Return values: `std::optional<T>` for absence under valid operation, never
  `nullptr` or `""`; `absl::StatusOr<T>` for invalid input or system errors;
  never sentinels (`-1.0`, `0.0`, `""`); no `optional` when presence is
  guaranteed. Multiple results return a named struct, never `std::pair`,
  `std::tuple` or out-parameters. A single `Msg* absl_nonnull out` for
  `FillXxx` observability helpers is fine.
- Parameters: `absl::Span<const T>` over `const std::vector<T>&`,
  `absl::string_view` for strings, `absl::flat_hash_map`/`set` unless sorted
  iteration is needed.
- Map and set keys are named structs with `auto operator<=>(const K&) const =
  default;` (or `operator==` plus `AbslHashValue`) and `AbslStringify`. Never
  `std::pair` or `std::tuple`. Production-config guard tests are exempt
  (`testing.md` §B).
- Naming: full words, never `m`, `c`, `s`, `v`, `e`, `cfg`, `res`, `val` (only
  `i` for integer indices and `T` for templates). When a loop converts a spec
  into a built object, name them `item_spec` and `item`. Acronyms are one word
  in CamelCase (`Rpc`, `Slo`). Name `StatusOr` variables after the value, never
  `*_or` or `maybe_*` (Abseil tip #181).
- Braces on every `if`/`for` body, including a one-line `continue;`.

## 5. Logging and defensive code

- Use the repository's logging and status macros (`ASSIGN_OR_RETURN`,
  `RETURN_IF_ERROR`, or its wrappers) and give the failing entity in the error
  message (`_ << "for order " << order.id()`).
- Start major functions with the repository's scope-logging helper, if it has
  one, instead of manual "Entering" logs. Context keys are named constants in
  one header, never raw strings.
- At most one `INFO` log per committed mutation, prefixed with the phase.
  Loops log start and end at `INFO` with the item count, items at verbose
  level; never `INFO` in a tight loop.
- No dual logging: never a table plus per-item `INFO` lines for the same items;
  a table plus one summary line. A pure helper that returns its result doesn't
  also log it; the caller reports it once.
- Decision points log why, with the values that decided. A branch that skips
  or lets lapse an action logs the reason. Log an object with its `ToString()`,
  not one field. Keep the default or disabled path silent.
- Read-only map lookups use `find()` (or `at()` when every key exists by
  construction), never `operator[]` on a non-const map, which inserts on a
  miss. That includes binding `const T& x = map[key];`.
- Lookup misses: `if (auto it = map.find(k); it == map.end()) continue;`. No
  null checks or `LOG(DFATAL)` branches for states that cannot occur; a
  `DCHECK` only documents a non-obvious guarantee.
- Size the failure mode to the branch. Inside a per-item loop, a state that
  "can't happen" whose only effect is skipping that item gets `LOG(DFATAL)` +
  record the item's outcome + `continue`: debug builds crash, production keeps
  every row labeled. Never return an error status there: one bad item would
  fail the whole run, every run, until a code change. A status is for state
  where continuing would produce a wrong result. When a reviewer asks whether a
  `DCHECK` should become a status, answer with this blast radius and the file's
  precedent.

## 6. Includes

- Strict include-what-you-use: the header for every symbol used (including the
  generated `.pb.h` of every message whose members you touch; a forward
  declaration from another header is not enough). `<cstdint>` for fixed-width
  integers, `<tuple>` for `std::tuple`, `<utility>` for `std::pair` and
  `std::move`, in test files too (`scripts/cq_sweep.py` checks these).
  clang-tidy's include cleaner is the authority (it flags `<compare>` as
  unused for a defaulted `operator<=>`).
- For every include in a touched file, name a symbol from it used in that
  file. None: delete it and its build dependency. Never touch includes for
  code the change didn't touch.
- After any include edit, run the repository's dependency cleanup tool on the
  target and rebuild. A header left behind by a dropped matcher is the most
  common post-refactor clang-tidy finding.

## 7. Small style

- Braces on every `if`/`for` body, including one-line `continue;`.
- Constant arrays and lookup tables live at namespace scope in the anonymous
  namespace, not function-local (Abseil tip #140).
- Name magic numbers that appear more than once (`kMicrosPerSecond`).
- Pure arithmetic helpers in headers are `constexpr`, never `inline`, with
  full parameter names.
- A function past ~60 lines, or with a second job, gets the new part extracted.
- Match a sibling loop's guards.
- Hoist a map lookup whose key doesn't change out of the loop; don't follow
  `contains()` with `[]` on the same key. Don't hoist a reference into a map
  the loop inserts into: a rehash invalidates it.
- Wrap a value in `std::optional(value)`, not `std::make_optional(value)`, when
  the other branch of a ternary is `std::nullopt`.
- Decision-record (observability) messages are filled by
  `FillXxx(..., Msg* absl_nonnull out)` helpers, one per topic
  (`lenses/common/design.md` §5).

## 8. Tests

- `ASSERT_THAT(x, SizeIs(n))` before indexing `x[0]`.
- Bind a value-returning lookup once per iteration; never call it twice in
  one `EXPECT_EQ(std::pair(...))`.
- Production-config guard tests may key on `std::pair<std::string,
  std::string>` or a concatenated string; the named-key-struct rule (§4) does
  not apply there (`lenses/common/testing.md` §B).
