# review-kit

Rules and scripts that check a change before a reviewer sees it. They work in
any git repository and from any editor or coding agent: the checks are plain
commands, and three git hooks run them at commit and push time.

Needs git and Python 3. No other dependency. The scripts are written for
Python 3.8 and later and have been run on 3.13 only.

## What is here

| Path | What it is |
|---|---|
| `lenses/` | Review lenses as Markdown: each one is the checklist a reviewer applies to one concern. `lenses/common/` (change hygiene, stack shape, design, code quality, testing, reviewer checklists, pattern scan, push gates) applies to every change; `lenses/c/`, `lenses/cpp/`, `lenses/cuda/`, `lenses/go/`, `lenses/kernel/`, `lenses/protobuf/`, `lenses/python/` and `lenses/typescript/` only when the diff touches that language. Load them into a coding agent or read them yourself. |
| `prompts/` | The prompt for an AI review of one commit, the prompt for an independent verifier, and the checklist of recurring findings both use. |
| `scripts/` | The checks. Each one runs on its own. |
| `hooks/` | `pre-commit`, `commit-msg` and `pre-push` wrappers, `install.sh`, `setup-repo.sh`, and `claude-stop.sh`, a Claude Code Stop hook. |
| `editors/` | VS Code tasks and an Emacs package that run the scripts. |
| `AGENTS.md` | Instructions that tell a coding agent when to read which lens and when to run which script. |
| `tests/` | Tests of the scripts. |

## Install

```
export REVIEWKIT_HOME=/path/to/review-kit        # in your shell profile
"$REVIEWKIT_HOME/hooks/install.sh" /path/to/repository
```

`install.sh` copies the three hooks into the repository and records the kit's
location in its git config. A hook that is already there and was not installed
by review-kit (git-lfs installs some) is moved to `<hook>.local`, and the
installed hook runs it after its own check passes. The same `.local` file is
the place for anything else you want to run after the kit.

To set a repository up for coding agents as well, run `setup-repo.sh` instead
of `install.sh`. It runs `install.sh`, then writes `AGENTS.md` at the
repository root from this kit's template with `<kit>` filled in. An
`AGENTS.md` that already exists is left alone for you to merge, and the script
points out a `CLAUDE.md` or `CLAUDE.local.md`, which Claude Code reads instead
of `AGENTS.md`:

```
"$REVIEWKIT_HOME/hooks/setup-repo.sh" /path/to/repository
```

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
| `cq_sweep.py [--staged \| --worktree \| --commit REV \| --range A..B] [--strict]` | Size over the limit, line numbers in comments, issue references outside a TODO, unbraced one-line bodies, missing or unused standard headers, long lines, single-letter names, map reads through `operator[]`, and similar nits on added lines. |
| `truth_audit.py [REV]` | Names in source-code comments and in the message that exist nowhere in the code, commit references that do not exist or are unmerged, `knob = value` claims that are not in the tree, duplicated paragraphs. Lines of prose files (Markdown, YAML, TOML, Dockerfiles) only reach the checklist. Then prints every added sentence as a checklist to verify by hand. |
| `stack_churn.py` | Lines a commit removes that an earlier commit of the same stack added. |
| `local_review.py` | Runs the configured AI reviewer on each commit and saves its report. |
| `gate.py` | All of the above for the whole stack, plus dead enum values, the configured linters and analyzers, and the review reports. Exit 0 records a pass. |
| `commit_msg.py FILE` | The commit message rules. In a Linux kernel tree, with `forbidMessage` at its default, only a `Signed-off-by`, `Co-developed-by` or `Co-authored-by` naming an AI tool is blocked, since the kernel asks for tool use to be disclosed in the changelog. |
| `llm_chat.py --model M [--fallback M2] [--base-url URL] [--key-env VAR] [--env-file PATH]` | Sends stdin (or `--prompt-file`) to an OpenAI-compatible endpoint and prints the reply: a ready-made `reviewCmd` or `verifyCmd` for a litellm proxy, vLLM, Ollama or a hosted API. Retries once on the fallback model after a 429, 5xx or timeout. |

## Configuration

Settings are git config keys, so they can be global or per repository. An
environment variable `REVIEWKIT_<KEY>` in upper snake case overrides a key
(`reviewkit.maxLines` becomes `REVIEWKIT_MAX_LINES`).

| Key | Default | Meaning |
|---|---|---|
| `reviewkit.base` | `origin/HEAD`, else `origin/main`, `origin/master`, `main`, `master` | Mainline ref the stack is measured from |
| `reviewkit.maxLines` | 150 | Changed lines (added plus deleted) per commit; 0 turns the check off, for a repository that takes large commits |
| `reviewkit.maxCols` | 80 | Column limit in the sweep; 0 turns it off |
| `reviewkit.churnLimit` | 5 | Lines of an earlier commit a later one may remove |
| `reviewkit.strict` | false | Make the pre-commit sweep block the commit |
| `reviewkit.forbidMessage` | AI and tool attribution | Regular expression a commit message must not match |
| `reviewkit.requireTrailers` | none | Comma-separated trailers every message must carry |
| `reviewkit.knownNames` | none | Comma-separated names the truth audit must not flag as stale: product names, services, config keys that no code defines |
| `reviewkit.lenses` | `auto` | Language lenses the AI review loads next to `common`: a comma-separated list of `c`, `cpp`, `cuda`, `go`, `kernel`, `protobuf`, `python`, `typescript`, or `auto` to pick them from the files each commit touches (`.cu` takes `cpp` and `cuda`; C files in a tree with `Kconfig` and `MAINTAINERS` at the root take `c` and `kernel`) |
| `reviewkit.lintCmd` | none | Linter to run on touched files; may be set several times |
| `reviewkit.tidyCmd` | none | Analyzer whose findings count only on added lines; may be set several times |
| `reviewkit.reviewCmd` | none | AI reviewer: a command that reads a prompt on stdin and prints the answer |
| `reviewkit.verifyCmd` | none | A second, independent reviewer, ideally another model |
| `reviewkit.agentStop` | true | Whether `hooks/claude-stop.sh` acts in this repository |
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

Without `reviewCmd` the gate skips the AI review and says so. With
`llm_chat.py` and a litellm proxy holding its key in an env file:

```
git config reviewkit.reviewCmd "python3 $REVIEWKIT_HOME/scripts/llm_chat.py \
  --base-url http://127.0.0.1:4001/v1 --env-file ~/stack/.env \
  --key-env LITELLM_MASTER_KEY --model gemini-3.8-flash-high"
```

`--fallback NAME` adds a second model, tried once when the first fails.
Name one that can write a whole review: a model whose server caps its
output, or that is too slow to finish within `TIMEOUT_S`, fails the review
anyway.

Once `reviewCmd` is set, the gate requires a clean report for every commit,
so run `local_review.py` before `gate.py`.
`local_review.py` also reads two environment variables: `PARALLEL`, the
number of reviews run at once (default 2), and `TIMEOUT_S`, the seconds
allowed per review (default 3600).

The hooks read `reviewkit.strict` and `reviewkit.home` from git config only;
`REVIEWKIT_HOME` in the environment overrides the second.

## With a coding agent

Claude Code reads `AGENTS.md` at the repository root natively (v2.1.277 and
later) as long as the repository has no `CLAUDE.md` or `CLAUDE.local.md`;
adding either one makes Claude Code read that file instead. Codex, Cursor,
Copilot, opencode and Gemini CLI read `AGENTS.md` too.

`hooks/claude-stop.sh` makes the sweep part of the agent loop: as a Claude
Code Stop hook it sweeps the files the agent changed, uncommitted and
untracked, and refuses to let the turn end while findings remain, feeding
them back to the agent. It acts only in repositories where `reviewkit.home`
is set, lets the agent stop on its second attempt so a finding it cannot fix
never loops, and `git config reviewkit.agentStop false` turns it off per
repository:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command",
  "command": "sh \"$REVIEWKIT_HOME/hooks/claude-stop.sh\""}]}]}}
```

Copy `AGENTS.md` into the repository (or append it to the file your agent
reads) and replace `<kit>` with this directory's path. The agent then reads
the lenses before coding and runs the gate before pushing. The hooks apply to
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

## Lenses

The lenses are written as what a reviewer checks, not as the history of any
one review. `lenses/common/` is language-neutral. A language lens holds the
concrete constructs for that language only, so a C++ repository never sees
Python docstring rules and a YAML-only change gets no C++ rules at all.
`local_review.py` pastes `common` plus the lenses for the languages a commit
touches into the review prompt; `reviewkit.lenses` overrides that choice.

The kit builds and runs no tests. The language lenses say which dynamic checks
a change's tests run under, and ask for the message to say so: `-race` in Go,
`compute-sanitizer` in CUDA, AddressSanitizer and UndefinedBehaviorSanitizer
in C and C++ (ThreadSanitizer too for concurrency changes), and KASAN, UBSAN,
lockdep and KCSAN in a kernel tree.

## Project profiles

The kit does not ship a formatter or an analyzer; it runs the ones you name.
These are the settings that make it match what each kind of project expects
from a reviewer. Set them per repository (`git config`), or globally with
`--global` where every repository agrees.

C++ with a compile database (`build/compile_commands.json`):

```
git config --add reviewkit.lintCmd '*.cc,*.cpp,*.h,*.hpp::clang-format --dry-run --Werror'
git config --add reviewkit.tidyCmd '*.cc,*.cpp,*.h,*.hpp::clang-tidy -p build --quiet --checks=clang-analyzer-*'
git config reviewkit.strict true
```

`--checks=clang-analyzer-*` adds the Clang Static Analyzer's path-sensitive
checks (null dereferences, leaks, use after free on some path) to whatever the
repository's `.clang-tidy` enables; clang-tidy appends `--checks` to the
file's list rather than replacing it.

CUDA, on top of the C++ profile (clang-format understands `.cu`; clang-tidy
needs the host pass of the compile database):

```
git config --add reviewkit.lintCmd '*.cu,*.cuh::clang-format --dry-run --Werror'
git config --add reviewkit.tidyCmd '*.cu,*.cuh::clang-tidy -p build --quiet --extra-arg=--no-cuda-version-check'
```

Go:

```
git config --add reviewkit.lintCmd '*.go::gofmt -l'
git config --add reviewkit.lintCmd '*.go::go vet ./...'
git config --add reviewkit.lintCmd '*.go::golangci-lint run --new-from-rev=origin/HEAD'
```

`gofmt -l` prints the unformatted files but exits 0, so pair it with
`test -z "$(gofmt -l ...)"` in a wrapper script if it must block.

Linux kernel tree (the `kernel` lens is picked up automatically from
`Kconfig` and `MAINTAINERS`):

```
git config reviewkit.requireTrailers 'Signed-off-by'
git config reviewkit.maxCols 80
git config --add reviewkit.lintCmd '*.c,*.h::scripts/checkpatch.pl --no-tree --strict -f'
git config reviewkit.base 'origin/master'
```

`checkpatch.pl -f` checks whole files; to check only the patch, run
`git format-patch` and `checkpatch.pl` on the result before the gate, or
wrap that in a script named by `lintCmd`.

A repository that takes large commits, such as a configuration or dotfiles
repository:

```
git config reviewkit.maxLines 0
```

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
