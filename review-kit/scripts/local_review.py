#!/usr/bin/env python3
"""Runs the configured AI reviewer on each commit of the stack and saves
stamped reports for gate.py.

Usage:
  local_review.py [--base B]

For each commit of merge-base(B, HEAD)..HEAD without a trustworthy report
for its fingerprint, it builds a prompt from <home>/prompts/review.md, runs
reviewCmd from the repository root with the prompt on stdin, takes the text
between a line `<<<LOCAL_REVIEW_REPORT` and a line `LOCAL_REVIEW_REPORT>>>`,
and saves it to <stateDir>/reviews/<fingerprint>.md behind a provenance line.
<home> is REVIEWKIT_HOME when it names a directory, else this kit; {{KIT}}
is always the kit that holds these scripts.

When verifyCmd is set, it first runs on <home>/prompts/verify.md (a neutral
brief: message and diff only), and its raw output reaches the main prompt as
{{CLAIMS}}. A command containing {prompt_file} gets the path of a temporary
file holding the prompt instead of stdin.

Placeholders in review.md: {{COMMIT}} {{SHORT}} {{BASE}} {{KIT}} {{STACK}}
{{MESSAGE}} {{DIFF}} {{CLAIMS}} {{RULES}} {{CHECKS}}. verify.md takes the
same set except {{RULES}}, {{CHECKS}} and {{CLAIMS}}. Every placeholder is
replaced in one pass, so text inside a diff or a rule file that looks like a
placeholder stays as it is.

Environment:
  PARALLEL   concurrent reviews (default 2)
  TIMEOUT_S  seconds per reviewer run (default 3600)

Exit codes:
  0  every commit has a report
  1  a run failed, timed out or printed no report
  2  reviewCmd is not configured, the stack is empty or could not be read
"""
import argparse
import concurrent.futures
import glob
import os
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

MAX_DIFF_CHARS = 200000
NO_VERIFIER = "(no independent verifier configured)"
NO_RULES = "(no rules directory)"
NO_CHECKS = "(no checks file)"
REPORT = re.compile(r"^<<<LOCAL_REVIEW_REPORT[ \t]*\n(.*?)\n"
                    r"LOCAL_REVIEW_REPORT>>>[ \t]*$", re.S | re.M)
PLACEHOLDER = re.compile(r"\{\{([A-Z]+)\}\}")


def report_path(state, fp):
    return os.path.join(state, "reviews", fp + ".md")


def fill(template, values):
    """Replaces every {{NAME}} that `values` knows in one pass."""
    return PLACEHOLDER.sub(
        lambda match: values.get(match.group(1), match.group(0)), template)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def rules_text(home):
    """Every rules/*.md, sorted by name, each behind a `### name` line."""
    paths = sorted(glob.glob(os.path.join(home, "rules", "*.md")))
    if not paths:
        return NO_RULES
    return "\n\n".join("### %s\n%s" % (os.path.basename(path),
                                       read_text(path).strip())
                       for path in paths)


def checks_text(home):
    path = os.path.join(home, "prompts", "checks.md")
    return read_text(path) if os.path.isfile(path) else NO_CHECKS


def cut_diff(diff, commit):
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    return (diff[:MAX_DIFF_CHARS]
            + "\n[diff cut at %d characters; read the whole diff with "
              "git show %s]\n" % (MAX_DIFF_CHARS, commit))


def run_reviewer(command, prompt, cwd, timeout):
    """Runs a reviewer command on `prompt`; returns (exit code, output)."""
    if "{prompt_file}" not in command:
        code, out, err = kit.run_shell(command, cwd, input_text=prompt,
                                       timeout=timeout)
        return code, out, err
    fd, path = tempfile.mkstemp(prefix="review-kit-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(prompt)
        code, out, err = kit.run_shell(
            command.replace("{prompt_file}", shlex.quote(path)), cwd,
            timeout=timeout)
        return code, out, err
    finally:
        os.remove(path)


def review(commit, ctx):
    """Reviews one commit if needed; returns a status line."""
    short = commit[:12]
    fp = kit.fingerprint_of(commit)
    path = report_path(ctx["state"], fp)
    problem = kit.saved_report_problem(path, fp)
    if problem is None:
        return "up to date (%s)" % path
    if problem != "missing":
        # Hand-written or truncated: review for real.
        os.remove(path)
    msg = kit.message(commit)
    values = {
        "COMMIT": commit,
        "SHORT": short,
        "BASE": ctx["base"],
        "KIT": kit.KIT_DIR,
        "STACK": ctx["stack"],
        "MESSAGE": msg,
        "DIFF": cut_diff(kit.commit_diff(commit), commit),
    }
    claims = NO_VERIFIER
    try:
        if ctx["verify_cmd"]:
            code, out, err = run_reviewer(
                ctx["verify_cmd"], fill(ctx["verify_template"], values),
                ctx["root"], ctx["timeout"])
            if code != 0:
                return ("FAILED: verifyCmd exited %d: %s; re-run"
                        % (code, err.strip()[-200:]))
            claims = out
        prompt = fill(ctx["review_template"],
                      dict(values, CLAIMS=claims, RULES=ctx["rules"],
                           CHECKS=ctx["checks"]))
        code, out, err = run_reviewer(ctx["review_cmd"], prompt, ctx["root"],
                                      ctx["timeout"])
    except subprocess.TimeoutExpired:
        return "TIMED OUT after %ds; re-run" % ctx["timeout"]
    except OSError as exc:
        return "FAILED: could not run the reviewer (%s)" % exc
    # The last block wins: a reviewer that echoes its prompt also echoes the
    # format example the prompt gives.
    found = REPORT.findall(out)
    if not found:
        return ("FAILED: no report in the reviewer's output (exit %d); "
                "re-run, never write a report by hand" % code)
    report = found[-1].strip()
    kit.write_atomic(path, kit.provenance_line(short, fp) + "\n"
                     + report + "\n")
    open_ids = kit.open_findings(report)
    if open_ids:
        return "%d open High/Medium (%s) -> %s" % (
            len(open_ids), ", ".join(open_ids), path)
    return "clean -> %s" % path


def main(argv):
    parser = argparse.ArgumentParser(
        description="Run the configured AI reviewer on each stack commit.")
    parser.add_argument("--base",
                        help="mainline ref (default: reviewkit.base)")
    args = parser.parse_args(argv)
    try:
        review_cmd = kit.config("reviewCmd").strip()
        if not review_cmd:
            print("local_review: reviewCmd is not configured; set it with "
                  "git config reviewkit.reviewCmd '<command>'")
            return 2
        parallel = max(1, int(os.environ.get("PARALLEL", "2")))
        timeout = int(os.environ.get("TIMEOUT_S", "3600"))
        top = kit.root()
        base_commit = kit.merge_base(kit.resolve_base(args.base))
        commits = kit.stack_commits(base_commit)
        if not commits:
            print("local_review: no commits in %s..HEAD" % base_commit[:12])
            return 2
        home = kit.home_dir()
        verify_cmd = kit.config("verifyCmd").strip()
        ctx = {
            "root": top,
            "home": home,
            "base": base_commit,
            "state": kit.state_dir(),
            "timeout": timeout,
            "review_cmd": review_cmd,
            "verify_cmd": verify_cmd,
            "review_template": read_text(
                os.path.join(home, "prompts", "review.md")),
            "verify_template": (read_text(os.path.join(home, "prompts",
                                                       "verify.md"))
                                if verify_cmd else ""),
            "rules": rules_text(home),
            "checks": checks_text(home),
            "stack": "\n".join("%s %s" % (c[:12], kit.subject(kit.message(c)))
                               for c in commits),
        }
    except (kit.KitError, OSError, ValueError) as exc:
        print("local_review: %s" % exc)
        return 2
    failed = False
    with concurrent.futures.ThreadPoolExecutor(parallel) as pool:
        futures = [pool.submit(review, commit, ctx) for commit in commits]
        for commit, future in zip(commits, futures):
            try:
                status = future.result()
            except (kit.KitError, OSError) as exc:
                status = "FAILED: %s" % exc
            print("%s: %s" % (commit[:12], status), flush=True)
            failed |= status.startswith(("FAILED", "TIMED OUT"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
