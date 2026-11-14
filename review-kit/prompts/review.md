Execution context: unattended pre-push review, started by local_review.py.
Nobody is watching; do not ask questions. Read-only: do not edit files, do not
commit, do not run builds or tests, and do not post anywhere.

Target: commit {{SHORT}} ({{COMMIT}}), which its author is about to push for
review. Review it the way a careful senior reviewer would, so the author can
fix everything before anyone else reads it.

The stack this commit belongs to, oldest first (merge base {{BASE}}):

```
{{STACK}}
```

If you can run commands, read file context with
`git show {{COMMIT}}:<path>` and the parent with `git show {{COMMIT}}~1:<path>`.
If you cannot, review from the message and diff below and say so in the
report.

## Commit message

```
{{MESSAGE}}
```

## Diff

```diff
{{DIFF}}
```

## Review passes

Each pass records findings as: location (`file:line` at {{SHORT}}), severity
(High / Medium / Low), how it could happen (trigger, mechanism, failure), the
fix, and the pass that found it.

A. **Correctness.** Does the code do what the message says, for every caller?
   Is behavior outside the stated scope preserved? Bugs and edge cases (empty
   input, zero, missing data, boundaries on both sides). Dead code, dead
   fields, dead parameters. Does a test fail when each new check is removed?
B. **Senior reviewer lens.** Every numbered check under "Senior reviewer
   lens" in the rules below.
C. **Independent reviewer lens.** Every numbered check under "Independent
   reviewer lens" in the rules below.
D. **Rules.** The rules below, for the languages in the diff, plus any
   contributor or style rules the repository itself carries (AGENTS.md,
   CONTRIBUTING, linter configuration). A violation on an added or edited
   line counts even when older lines of the file do the same.
E. **Truth.** Every comment the diff adds and every sentence of the message
   is true of the code at {{SHORT}} and at this position in the stack. A
   sentence about a later commit's behavior, or about something not merged
   yet, says so.
F. **Independent verifier.** The claims below came from a separate reviewer
   that saw only the message and the diff. Fact-check each one at the line it
   cites and keep only the ones you confirm.
G. **Recurring findings.** Every item of the checklist below.
H. **Risk.** Rate the change Low / Mid / High risk in one sentence.

## Verify and merge

Drop any finding you cannot confirm at the cited line. Merge duplicates across
passes and keep every pass name. Order High, then Medium, then Low. A
suggested fix is a claim too: carry every condition your evidence states into
the suggested wording.

## Report

Print the report in your final message between a line
`<<<LOCAL_REVIEW_REPORT` and a line `LOCAL_REVIEW_REPORT>>>`. It contains: the
commit, the risk, whether you could read files beyond the diff, then every
finding under a heading `### H1 — ...`, `### M1 — ...` or `### L1 — ...`
(numbered per severity), each with its location, how it could happen, the fix
and the passes that found it. With no findings, list what each pass checked.

## Independent verifier's claims

{{CLAIMS}}

## Rules

{{RULES}}

## Recurring findings checklist

{{CHECKS}}
