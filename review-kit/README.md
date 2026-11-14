# review-kit

Rules and scripts that check a change before a reviewer sees it. They work in
any git repository and from any editor or coding agent: the checks are plain
commands, and three git hooks run them at commit and push time.

Needs git and Python 3. No other dependency. The scripts are written for
Python 3.8 and later and have been run on 3.13 only.

## What is here

| Path | What it is |
|---|---|
| `rules/` | Engineering rules as Markdown: change hygiene, stack shape, design, C++, code quality, testing, review checklists, push gates. Load them into a coding agent or read them yourself. |
| `prompts/` | The prompt for an AI review of one commit, the prompt for an independent verifier, and the checklist of recurring findings both use. |
| `scripts/` | The checks. Each one runs on its own. |
| `hooks/` | `pre-commit`, `commit-msg` and `pre-push` wrappers, and `install.sh`. |
| `editors/` | VS Code tasks and an Emacs package that run the scripts. |
| `AGENTS.md` | Instructions that tell a coding agent when to read which rule and when to run which script. |
| `tests/` | Tests of the scripts. |

## Install

```
export REVIEWKIT_HOME=/path/to/review-kit        # in your shell profile
"$REVIEWKIT_HOME/hooks/install.sh" /path/to/repository
```

`install.sh` copies the three hooks into the repository and records the kit's
location in its git config. It does not overwrite a hook it did not install.

To use the kit in every repository instead, point git at the hooks once:

```
git config --global core.hooksPath "$REVIEWKIT_HOME/hooks"
git config --global reviewkit.home "$REVIEWKIT_HOME"
```

## What runs when

| When | Check | Blocks? |
|---|---|---|
| `git commit` (pre-commit) | `cq_sweep.py --staged`: suspected nits on the staged lines | Only with `reviewkit.strict` set to true |
| `git commit` (commit-msg) | `commit_msg.py`: no AI or tool attribution, no duplicated paragraph, required trailers | Yes |
| Before pushing, by hand | `local_review.py`, then `gate.py` | `gate.py` exits non-zero |
| `git push` (pre-push) | The pushed commits passed `gate.py` in their current form | Yes |

A gate pass is recorded per commit fingerprint (message body plus net patch
lines), so a rebase keeps it and any edit voids it.

The push check covers the commits that no remote has yet, so history fetched
from one remote can be pushed to another (a fork) without a pass. Before a
repository's first push or fetch there is no mainline to measure a stack
from, so commits on the base branch are let through and the hook says so.

## The scripts

Run them from anywhere inside the repository. A "stack" is the commits between
the merge base with the mainline and `HEAD`.

| Script | What it checks |
|---|---|
| `cq_sweep.py [--staged \| --commit REV \| --range A..B] [--strict]` | Size over the limit, line numbers in comments, issue references outside a TODO, unbraced one-line bodies, missing or unused standard headers, long lines, single-letter names, map reads through `operator[]`, and similar nits on added lines. |
| `truth_audit.py [REV]` | Names in comments and in the message that exist nowhere in the code, commit references that do not exist or are unmerged, `knob = value` claims that are not in the tree, duplicated paragraphs. Then prints every added sentence as a checklist to verify by hand. |
| `stack_churn.py` | Lines a commit removes that an earlier commit of the same stack added. |
| `local_review.py` | Runs the configured AI reviewer on each commit and saves its report. |
| `gate.py` | All of the above for the whole stack, plus dead enum values, the configured linters and analyzers, and the review reports. Exit 0 records a pass. |
| `commit_msg.py FILE` | The commit message rules. |

## Configuration

Settings are git config keys, so they can be global or per repository. An
environment variable `REVIEWKIT_<KEY>` in upper snake case overrides a key
(`reviewkit.maxLines` becomes `REVIEWKIT_MAX_LINES`).

| Key | Default | Meaning |
|---|---|---|
| `reviewkit.base` | `origin/HEAD`, else `origin/main`, `origin/master`, `main`, `master` | Mainline ref the stack is measured from |
| `reviewkit.maxLines` | 150 | Changed lines (added plus deleted) per commit |
| `reviewkit.maxCols` | 80 | Column limit in the sweep; 0 turns it off |
| `reviewkit.churnLimit` | 5 | Lines of an earlier commit a later one may remove |
| `reviewkit.strict` | false | Make the pre-commit sweep block the commit |
| `reviewkit.forbidMessage` | AI and tool attribution | Regular expression a commit message must not match |
| `reviewkit.requireTrailers` | none | Comma-separated trailers every message must carry |
| `reviewkit.lintCmd` | none | Linter to run on touched files; may be set several times |
| `reviewkit.tidyCmd` | none | Analyzer whose findings count only on added lines; may be set several times |
| `reviewkit.reviewCmd` | none | AI reviewer: a command that reads a prompt on stdin and prints the answer |
| `reviewkit.verifyCmd` | none | A second, independent reviewer, ideally another model |
| `reviewkit.stateDir` | `review-kit/` inside `.git` | Where reports, overrides and gate passes are kept; a path inside the work tree is refused |

`lintCmd` and `tidyCmd` take the form `globs::command`. The command runs from
the repository root with the matching touched files appended:

```
git config --add reviewkit.lintCmd '*.py::ruff check'
git config --add reviewkit.lintCmd '*.cc,*.h::clang-format --dry-run --Werror'
git config --add reviewkit.tidyCmd '*.cc,*.h::clang-tidy -p build'
```

`reviewCmd` is any command line that takes a prompt and prints a reply. Use
`{prompt_file}` in the command when the tool wants a file instead of stdin:

```
git config --global reviewkit.reviewCmd 'my-agent --print'
git config --global reviewkit.verifyCmd 'other-agent --read {prompt_file}'
```

Without `reviewCmd` the gate skips the AI review and says so.
`local_review.py` also reads two environment variables: `PARALLEL`, the
number of reviews run at once (default 2), and `TIMEOUT_S`, the seconds
allowed per review (default 3600).

The hooks read `reviewkit.strict` and `reviewkit.home` from git config only;
`REVIEWKIT_HOME` in the environment overrides the second.

## With a coding agent

Copy `AGENTS.md` into the repository (or append it to the file your agent
reads) and replace `<kit>` with this directory's path. The agent then reads
the rules before coding and runs the gate before pushing. The hooks apply to
the agent's commits and pushes as they do to yours.

## With an editor

- VS Code: copy `editors/vscode-tasks.json` to `.vscode/tasks.json`, then
  run a task from "Tasks: Run Task".
- Emacs: load `editors/review-kit.el`, then `M-x review-kit-gate`. Output is a
  compilation buffer, so `next-error` jumps to each finding.
- Anything else: bind a key to `python3 $REVIEWKIT_HOME/scripts/gate.py`.

## With the pre-commit framework

In a repository that uses [pre-commit](https://pre-commit.com), that framework
owns the hook files, so add the commit-time checks as local hooks instead of
running `install.sh`. This snippet has not been run against the framework:

```yaml
repos:
  - repo: local
    hooks:
      - id: review-kit-sweep
        name: review-kit sweep
        entry: sh -c 'python3 "$REVIEWKIT_HOME/scripts/cq_sweep.py" --staged'
        language: system
        pass_filenames: false
      - id: review-kit-message
        name: review-kit commit message
        entry: sh -c 'python3 "$REVIEWKIT_HOME/scripts/commit_msg.py" "$1"' --
        language: system
        stages: [commit-msg]
```

The push check reads the list of pushed refs that git writes to the pre-push
hook, so it is not included here: run `gate.py` by hand before pushing in
such a repository.

## Limits

- The checks are text heuristics over diffs. A clean run means none of the
  listed patterns matched, not that the change is correct.
- The C++ checks have no parser behind them: the map checks know a name is a
  map only when it is declared in the same file.
- The stack checks need a linear stack. A range with a merge commit is
  reported as not checked.
- `git push --no-verify` skips the push hook, as it skips every hook.
- The AI review is only as good as the command behind `reviewCmd`. The gate
  checks that a report exists and has no open High or Medium finding, not
  that the review was thorough.

## Tests

```
python3 -m unittest discover -s tests -v
```
