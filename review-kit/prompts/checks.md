# Recurring findings: checks every review runs explicitly

Each item is a class of finding that reached reviewers on changes that had
passed every mechanical check. "The change" is the commit under review. Add a
new class of finding here, so every reviewer runs the same list.

1. Every early return, clamp (`std::max`/`std::min`, `max()`/`min()`), guard
   and fallback the change adds to non-test code: name the test that fails
   when it is removed. None is a finding.
2. Every assertion the change adds: if the expected value equals the type's
   default (0, 0.0, false, "", the first enum value), deleting the setter
   still passes. That is a finding.
3. Every comment or message sentence with an absolute ("every", "always",
   "never", "only", "fail closed", "in every run"): true on every path,
   early returns included. Where two stated rules cover the same case, the
   sentence says which one wins.
4. Every comment on an observability field (a metric, a log column, a debug
   field): its presence rule names every case the producer leaves it absent,
   at 0, negative or at a fail-closed value. Check against the producer code,
   not the field name.
5. Changed lines (added plus deleted) well over 150: up to ~200 lines, a Low
   note only when the extra size comes from a second, separable problem. 150 is
   a soft ceiling: a single-problem change that is a final state is not a
   finding between 150 and ~200, nor is a pure move or a golden-file update at
   any size. Well past ~200 lines, where `lenses/common/change_hygiene.md` §1
   expects a split, a single-problem change also gets a Low note asking for one,
   unless it is a pure move or a generated or golden-file update.
6. Test claims in the commit message (which tests ran, mutation results,
   coverage) match the code and tests in the change.
7. Every line the change adds or edits follows the repository's current
   standards, even where older lines of the same file do not. A violation on
   an added line is Medium, not a style Low, and "the file already does this"
   is no reason to keep it. Includes a read-only lookup through a map's
   `operator[]` (binding `const auto& x = m[key];`), which inserts on a miss.
8. Performance on added lines: a map lookup repeated inside a loop with a key
   that does not change in that loop (hoist it); `contains()` followed by
   `[]` or `find()` on the same key; no `reserve()` when the final size is
   known before filling; a new ordered container where order is not needed;
   chained string `+`; a new `const std::string&` parameter where a view
   works; an object built from scratch on every loop iteration.
9. Every synthetic fixture the change adds or edits (test config, test data)
   is a shape production can produce. Name the generator or loader for each
   structure and check its rules (uniqueness, required pairs, which entity
   may reference which). A fixture no generator can emit is Medium.
10. Where the change removes a check, or the message says a check is not
    needed because another mechanism covers the case: name the test in which
    only that mechanism produces the expected outcome. None is a finding.
11. Every hard failure the change adds inside a per-item loop (a returned
    error, an exception, an assertion that aborts): state what the branch
    would do if it only skipped the item. If the answer is "skip one item",
    the hard failure is Medium: it fails the whole run, on every run while
    the input repeats. The fix is to log loudly (fatal in debug builds),
    record the item's outcome and continue. The reverse is a finding too: a
    `continue` in such a loop that records no outcome and logs nothing.
12. Every enum value or schema field the change adds: name the code in this
    stack that sets it or reads it. An enum value whose only uses are `==` /
    `!=` comparisons, `case` labels or skip lists has no producer: High. An
    enum value comment that describes a branch that no longer assigns that
    value is Medium. A finding declined as "fixed in a later change" is valid
    only when the named symbol exists in the stack's non-comment code.
13. Every outcome, reject-reason or skip label (enum value, metric label, log
    row) the change assigns, renames or re-documents where more than one cap,
    budget or guard can stop the same item: name the knob or condition each
    label stands for, then answer from the code, the other caps included,
    "with only that one lifted, would this item go through?" An item another
    cap would still stop carries the wrong label: Medium, or High when the
    label feeds a metric a knob is tuned by. Also check that identical items
    get the same labels whatever order they are processed in, that the
    label's doc states that counterfactual and not the code path that assigns
    it, and that a test has one item hitting both limits.
14. Stack churn (`lenses/common/stack_shape.md`). When the change has unmerged parent
    commits by the same author, list what it deletes, moves, hides, reformats
    or rewords that a parent added: code, tests, output text, help text.
    `scripts/stack_churn.py` prints the removed lines; hiding or re-parsing a
    parent's output without touching its lines shows only in the parents'
    diffs. More than extending a statement (one more argument, condition or
    column) is Medium, with the fix "fold it into the parent commit". A
    parent whose subject says pure move is exempt.
15. One decider per decision (`lenses/common/stack_shape.md`). Every place the change
    matches, splits or regex-parses text that another layer of the same
    feature produces (`value.includes('(frozen: ')`, a regex over a marker,
    `header.split(' ')[0]`, a join on keys cut from rendered output): Medium.
    The producing layer decides and passes the result; the consumer renders
    it. Also Medium: a structured value printed into a string and parsed
    back, and one term decided in two places or two languages.
16. Fix the producer, not the consumer (`lenses/common/design.md` §2). Every
    branch the change adds to recover from or compensate for a bad input
    (handling A by producing B): name where A is produced and whether sibling
    producers already prevent it (set the companion field, apply the guard).
    A branch that fires only because one producer omits what its siblings
    set is High, with the fix "set it at that producer, or block A, and drop
    the branch". So is a description that cites that omission as proof the
    branch is reachable. Downstream recovery stays only for inputs no
    producer can prevent (external data, user input, partial failures), and
    the description says why the source cannot.
17. Edits to existing comments (`lenses/common/code_quality.md` §1). When the
    change updates an existing comment or doc (a rename, a local behavior
    change, a targeted fix) and condenses, deletes or rewrites surrounding
    sentences that the change did not make wrong: Medium, with the fix
    "restore the original structure and edit only the affected words in
    place". Do not flag simplifications on untouched lines of the block
    unless this change made them false or an added line states something
    false. Nor flag a larger rewrite when the change restructures the code
    the whole comment describes and the description says so.
18. Description length (`lenses/common/change_hygiene.md` §3). Prose above
    the first `<details>` block, trailers excluded, over ~150 words: Low,
    naming the sentences to cut or collapse: ones that narrate the diff,
    list edge cases, retell the parent change, or put evidence or a diagram
    outside a collapsed block. ~150 is a soft ceiling; a sentence the
    description needs to be true is not a finding.
19. New configuration fields (`lenses/common/design.md` §2). Every field the
    change adds or first reads whose valid set is narrower than its type:
    name the validator line that rejects the rest and the test that
    exercises it. None is Medium; High when an invalid value silently
    changes behavior (a helper clamps it, or it turns another check off).
    For a field only one mode reads, also name the line that rejects it in
    the other modes, and check that no early return in the validator skips
    it; Medium otherwise.
20. Checks that configuration can run alone (`lenses/common/testing.md` §A).
    For each such check, in each mode where it runs alone, name the test
    where it keeps the item and the test where it drops it. A mode with
    only one of the two is Medium: the mutation "this check always passes"
    stays green there.
21. Constants turned into settings (`lenses/common/code_quality.md` §1).
    Every constant the change replaces with a configuration field: the
    reason for the old value, and what each allowed value trades off, are
    in the field's doc. A rationale deleted with the constant is Medium.
22. Fallbacks for unset configuration (`lenses/common/design.md` §1). Every
    fallback the change gives an unset or empty configuration message
    ("unset keeps today's behavior"): name the production configuration
    that relies on it. None is Medium: require the configuration to say
    what it wants and validate it. A metric or log that reports the
    fallback's check as off while it runs is part of the same finding.
