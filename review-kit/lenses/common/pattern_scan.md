# Pattern Scan Lens

Before any design or code, for every change: learn how the directory already solves similar problems.

A small change (see "Small changes" in the kit's AGENTS.md) needs only a
one-line note: the closest precedent and why the change follows it.

A solution that ignores the local pattern costs a review round at best, and at
worst hides a bug the local pattern would have caught. Logic with branches
written inline in a test, where the directory keeps such logic in a helper
library with synthetic tests, stays wrong and green because only one input
ever exercises it.

## 1. Scan before deciding where the code goes

For every directory the change touches (and its parent, if the change adds a
new file):

1. List every file and open the ones whose names or symbols relate to the
   problem. For each, note what it computes, where its logic lives (helper
   library, test, binary) and how that logic is tested.
2. Read the history: the last ~20 changes to the directory (`git log -n 20 --
   <dir>` or `jj log -r 'files("<dir>")' --limit 20`), and read the 3-5 most
   relevant in full. Note how comparable changes were split, what their
   descriptions contained and what reviewers asked for in them.
3. Find the closest precedent: the existing function, test or change that
   solves the most similar problem. The new code follows its placement, naming,
   key types, error handling, test shape and split into changes, unless there
   is a stated reason not to.
   - Exception: where the repository has written team standards (for example
     wrapper macros for logging and status), new lines follow the standards even
     in a file full of the older convention. Leave untouched lines alone.
4. Search the repository (git grep or an equivalent index) for an existing
   helper, formula or pattern before writing one.

## 2. Write the result down before coding

Post a short "Pattern scan" note in the reply to the user (5-10 lines):

- Files read, and the closest precedent (a helper and its test, a guard test, a
  past change).
- Where the new logic will live and why that matches the precedent.
- How each branch will be tested (synthetic unit test next to the helper,
  production-config guard, or both).
- The planned split into changes, mirroring how the precedent landed, and what
  each change leaves in its final form (`stack_shape.md`).
- Any deliberate deviation from the local pattern and its reason. This
  sentence also goes into the change description.

No code is written until this note exists. If the scan changes the plan for
work already in flight, say so and re-plan before continuing.

## 3. Re-check before pushing

Compare the final diff with the note. If the code drifted from the precedent
(logic moved inline, a new key type, a different test shape), bring it back or
state the reason in the description.
