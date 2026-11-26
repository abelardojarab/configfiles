#!/usr/bin/env python3
"""The pre-push gate: every check that must pass before a stack is pushed.

Usage:
  gate.py [--base B]
  gate.py --check-push REMOTE_NAME REMOTE_URL   (git's pre-push hook)

Without --check-push it checks the stack merge-base(B, HEAD)..HEAD (B
defaults to reviewkit.base) and prints one `######## <name>` section per
check: a clean work tree, the commit message rules, the truth audit (flags
may be overridden in <stateDir>/truth_overrides/<fingerprint>.txt with lines
`<exact flag line> :: <reason of 20+ characters>`), unused
proto enum values, stack churn, reads through a C++ map's operator[],
lintCmd and tidyCmd, and, when reviewCmd is set, the saved AI review reports.
The code-quality sweep, a warning for each commit over reviewkit.maxLines
changed lines (a soft ceiling; off when it is 0), a warning for each commit
whose message has more than reviewkit.maxWords words above its first
<details> block (off when it is 0), and a warning for each commit that
touches reviewkit.impactPaths without a Production impact block or a
"Production impact: none (" line, are printed without failing. On a
pass it writes a stamp to <stateDir>/gate_pass/ that the pre-push check
accepts for 7 days while the commits keep their fingerprints.

With --check-push it reads git's pre-push lines on stdin and accepts the
push only when one stamp younger than 7 days holds the fingerprint of every
commit being pushed, and every such commit's message still passes the
commit message rules. The commits being pushed are the ones no remote has
yet, so history fetched from one remote can be pushed to another. In a
repository with no remote-tracking branch at all, the base branch's own
commits are not checked: before the first push there is nothing to measure
a stack from.

Exit codes:
  0  every check passed (the push is covered, with --check-push)
  1  at least one check failed (the push is not covered)
  2  the stack is empty or could not be read
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cq_sweep  # noqa: E402
import kit  # noqa: E402
import stack_churn  # noqa: E402
import truth_audit  # noqa: E402

STAMP_MAX_AGE_S = 7 * 24 * 3600
ZERO_HASH = re.compile(r"^0+$")
TIDY_FINDING = re.compile(r"^(.+?):(\d+):(\d+):", re.M)
QUALIFIED = re.compile(r"\b([A-Z]\w*::[A-Za-z_]\w+)\b")


def section(name, body):
    print("\n######## %s" % name)
    if body:
        print(body.rstrip("\n"))


def flag_lines(audit_out):
    """The flag lines truth_audit printed under `== Flags`."""
    part = audit_out.partition("\n== Flags\n")[2]
    part = part.partition("\n== Manual checklist")[0]
    return [line.strip() for line in part.splitlines()
            if line.strip() and line.strip() != "(none)"]


def override_reasons(path):
    """{flag line: reason} from a truth-audit override file."""
    reasons = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                flag, sep, reason = line.strip().partition(" :: ")
                if sep and len(reason.strip()) >= kit.MIN_REASON_CHARS:
                    reasons[flag.strip()] = reason.strip()
    return reasons


def added_proto_enums(diff):
    """[(path, enum name, value name)] for enum values a diff adds to .proto
    files, value 0 and *_UNSPECIFIED left out."""
    out = []
    for _, new, hunks in kit.sections(diff):
        if not new or not new.endswith(".proto"):
            continue
        for hunk in hunks:
            enum_name = None
            for line in hunk[4]:
                text = line[1:] if line[:1] in "+- " else line
                code = text.split("//", 1)[0]
                opened = re.match(r"\s*enum\s+([A-Za-z_]\w*)\s*\{", code)
                if opened and not line.startswith("-"):
                    enum_name = opened.group(1)
                    continue
                if re.match(r"\s*\}", code) and not line.startswith("-"):
                    enum_name = None
                    continue
                if line.startswith("+"):
                    value = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=\s*(\d+)\s*"
                                     r"(?:\[[^\]]*\]\s*)?;", code)
                    if (value and value.group(2) != "0"
                            and not value.group(1).endswith("_UNSPECIFIED")):
                        out.append((new, enum_name or "", value.group(1)))
    return out


def has_real_use(value_name, files_text):
    """Whether `value_name` appears in code other than an ==/!= comparison or
    a case label. files_text: {path: text}."""
    word = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(value_name)
                      + r"(?![A-Za-z0-9_])")
    skip = re.compile(
        r"(?:==|!=)\s*(?:[\w:.]*(?:::|\.))?" + re.escape(value_name)
        + r"(?![A-Za-z0-9_])"
        r"|(?<![A-Za-z0-9_])" + re.escape(value_name) + r"\s*(?:==|!=)"
        r"|\bcase\s+(?:[\w:.]*(?:::|\.))?" + re.escape(value_name)
        + r"\s*:(?!:)")
    for path, text in files_text.items():
        for line in text.splitlines():
            code = kit.split_comment(path, line)[0]
            if word.search(skip.sub("", code)):
                return True
    return False


def declined_problems(report_text, corpus):
    """Problems with a report's `## Declined` reasons: too short, or citing
    a Class::member that exists neither in the stack's code nor at HEAD."""
    problems = []
    for fid, reason in sorted(kit.declined_reasons(report_text).items()):
        if len(reason) < kit.MIN_REASON_CHARS:
            problems.append("%s under '## Declined' has a reason shorter "
                            "than %d characters" % (fid, kit.MIN_REASON_CHARS))
            continue
        for qual in sorted(set(QUALIFIED.findall(reason))):
            cls, member = qual.split("::", 1)
            if kit.has_word(cls, corpus) and kit.has_word(member, corpus):
                continue
            code, _, _ = kit.run_git(["grep", "-q", "-I", "--no-color", "-F",
                                      "-e", qual, "HEAD", "--"])
            if code != 0:
                problems.append("%s decline cites `%s`, which exists neither "
                                "in the stack's code nor at HEAD"
                                % (fid, qual))
    return problems


def parse_command_spec(value):
    """(globs, command) from a `[globs::]command` setting."""
    prefix, sep, rest = value.partition("::")
    if sep and prefix and not re.search(r"\s", prefix):
        return [g for g in prefix.split(",") if g], rest.strip()
    return [], value.strip()


def matching(files, globs):
    if not globs:
        return list(files)
    return [path for path in files
            if any(fnmatch.fnmatch(os.path.basename(path), g) for g in globs)]


def normalize_finding_path(path, top):
    path = path.strip()
    if os.path.isabs(path):
        real = os.path.realpath(path)
        path = os.path.relpath(real, os.path.realpath(top))
    while path.startswith("./"):
        path = path[2:]
    return path


def run_commands(top, files, added, failures):
    """lintCmd and tidyCmd over the files the stack touches."""
    for key in ("lintCmd", "tidyCmd"):
        for value in kit.config_all(key):
            globs, command = parse_command_spec(value)
            targets = [f for f in matching(files, globs)
                       if os.path.isfile(os.path.join(top, f))]
            if not command or not targets:
                section("%s (%s)" % (key, command or value),
                        "skipped: no touched file matches")
                continue
            line = command + " " + " ".join(shlex.quote(f) for f in targets)
            try:
                code, out, err = kit.run_shell(line, top)
            except OSError as exc:
                code, out, err = 127, "", str(exc)
            section("%s (%s)" % (key, command), out + err)
            if key == "lintCmd":
                if code != 0:
                    failures.append("lintCmd '%s' exited %d" % (command, code))
                continue
            on_change, elsewhere = [], []
            for path, line_no, _ in TIDY_FINDING.findall(out + "\n" + err):
                rel = normalize_finding_path(path, top)
                spot = "%s:%s" % (rel, line_no)
                bucket = (on_change if int(line_no) in added.get(rel, {})
                          else elsewhere)
                if spot not in bucket:
                    bucket.append(spot)
            if on_change:
                failures.append("tidyCmd '%s' findings on lines the stack "
                                "adds: %s" % (command, ", ".join(on_change)))
            if elsewhere:
                print("(tidyCmd findings on lines the stack does not add, "
                      "out of scope: %s)" % ", ".join(elsewhere))
            if code != 0 and not on_change and not elsewhere:
                failures.append("tidyCmd '%s' failed: command failed with "
                                "exit %d and printed no finding"
                                % (command, code))


_IMPACT_BLOCK = re.compile(r"<summary>\s*Production impact\s*</summary>"
                           r"|^Production impact: none \(", re.I | re.M)


def _missing_impact(commits):
    """Returns (commit, matching files) for each commit lacking an impact note.

    A commit lacks one when it touches a file whose name matches a glob of
    reviewkit.impactPaths and its message has neither a Production impact
    block nor a `Production impact: none (` line. An empty setting lists none.
    """
    globs = [pattern.strip()
             for pattern in kit.config("impactPaths").split(",")
             if pattern.strip()]
    if not globs:
        return []
    lacking = []
    for commit in commits:
        touched = matching(kit.commit_files(commit), globs)
        if touched and not _IMPACT_BLOCK.search(kit.message(commit)):
            lacking.append((commit, touched))
    return lacking


def _prose_words(message):
    """Returns the words of a commit message above its first <details> block,
    trailers left out: what a reviewer reads before the collapsed evidence."""
    body, _ = kit.split_message(message)
    words = 0
    for line in body.splitlines():
        if line.lstrip().startswith("<details"):
            break
        words += len(line.split())
    return words


def stamp_key(commits):
    return hashlib.sha256("\n".join(sorted(commits)).encode()).hexdigest()[:16]


def load_stamps(state):
    """Stamps younger than STAMP_MAX_AGE_S."""
    directory = os.path.join(state, "gate_pass")
    if not os.path.isdir(directory):
        return []
    stamps, now = [], time.time()
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                stamp = json.load(fh)
        except (OSError, ValueError):
            continue
        if (isinstance(stamp, dict)
                and now - stamp.get("time", 0) < STAMP_MAX_AGE_S):
            stamps.append(stamp)
    return stamps


def run_gate(base_arg):
    try:
        top = kit.root()
        state = kit.state_dir()
        base_ref = kit.resolve_base(base_arg)
        base_commit = kit.merge_base(base_ref)
        head_start = kit.rev_parse("HEAD")
        commits = kit.stack_commits(base_commit, head_start)
        max_lines = kit.config_int("maxLines")
        max_words = kit.config_int("maxWords")
        max_cols = kit.config_int("maxCols")
        churn_limit = kit.config_int("churnLimit")
    except kit.KitError as exc:
        print("gate: cannot read the stack: %s" % exc)
        return 2
    if not commits:
        print("gate: no commits in %s..HEAD (base %s)"
              % (base_commit[:12], base_ref))
        return 2

    failures = []
    fingerprints = {}
    overrides_used = {}
    try:
        section("Stack", "base %s (%s), %d commit(s):\n%s" % (
            base_ref, base_commit[:12], len(commits),
            "\n".join("%s %s" % (c[:12], kit.subject(kit.message(c)))
                      for c in commits)))

        status = kit.git("status", "--porcelain=v1", "-z",
                         "--untracked-files=no", "--ignore-submodules=dirty")
        dirty, entries = [], status.split("\0")
        while entries:
            entry = entries.pop(0)
            if len(entry) > 3:
                dirty.append(entry[3:])
                if entry[0] in "RC":
                    # -z prints a rename's source as its own entry.
                    entries = entries[1:]
        section("Work tree", "\n".join(dirty) or "clean")
        if dirty:
            failures.append("tracked files differ from HEAD (%s): commit or "
                            "stash them, so the checks see what is pushed"
                            % ", ".join(dirty[:10]))

        size_warnings, word_warnings = [], []
        for commit in commits:
            short = commit[:12]
            msg = kit.message(commit)
            fp = kit.fingerprint_of(commit)
            fingerprints[commit] = fp
            problems = kit.message_problems(msg)
            section("Commit message %s" % short,
                    "\n".join(problems) or "ok")
            failures += ["%s: %s" % (short, p) for p in problems]

            flags, issues, sources = truth_audit.audit(commit, base_commit)
            audit_out = truth_audit.render(flags, issues, sources)
            section("Truth audit %s" % short, audit_out)
            flags = flag_lines(audit_out)
            if flags:
                path = os.path.join(state, "truth_overrides", fp + ".txt")
                reasons = override_reasons(path)
                for flag in flags:
                    if flag in reasons:
                        print("OVERRIDDEN %s :: %s" % (flag, reasons[flag]))
                        overrides_used.setdefault(commit, []).append(
                            "%s :: %s" % (flag, reasons[flag]))
                open_flags = [f for f in flags if f not in reasons]
                if open_flags:
                    failures.append(
                        "%s: truth audit flags %s: fix each; for a false "
                        "positive add the exact flag line, ' :: ' and a "
                        "reason of %d+ characters to %s"
                        % (short, " | ".join(open_flags),
                           kit.MIN_REASON_CHARS, path))

            diff = kit.commit_diff(commit)
            size = kit.changed_line_count(diff)
            if (max_lines > 0 and size > max_lines
                    and not kit.MOVE_ONLY.search(kit.subject(msg))):
                size_warnings.append(
                    "WARNING (not blocking): %s: %d changed lines (soft "
                    "ceiling %d): check it is one problem "
                    "(lenses/common/change_hygiene.md section 1)"
                    % (short, size, max_lines))
            words = _prose_words(msg)
            if max_words > 0 and words > max_words:
                word_warnings.append(
                    "WARNING (not blocking): %s: %d words of message prose "
                    "above the first <details> block (soft ceiling %d): cut "
                    "what the diff already says and collapse evidence "
                    "(lenses/common/change_hygiene.md section 3)"
                    % (short, words, max_words))

            section("Code-quality sweep %s (not blocking)" % short,
                    cq_sweep.render(cq_sweep.sweep_commit(commit, max_lines,
                                                          max_cols)))

        section("Size (not blocking)", "\n".join(size_warnings) or "ok")
        section("Description length (not blocking)",
                "\n".join(word_warnings) or "ok")

        files = kit.changed_files(base_commit, head_start)
        code_files = {}
        for path in files:
            if (path.endswith(".proto") or kit.is_markdown(path)
                    or kit.is_test_path(path)):
                continue
            text = kit.file_text(head_start, path)
            if text is not None:
                code_files[path] = text
        dead = []
        for commit in commits:
            for path, _, value in added_proto_enums(kit.commit_diff(commit)):
                if not has_real_use(value, code_files):
                    dead.append("%s: proto enum value %s (%s) is used nowhere "
                                "in the stack's code, or only in ==/!= "
                                "comparisons and case labels: drop it or add "
                                "the code that sets it"
                                % (commit[:12], value, path))
        section("Proto enum values", "\n".join(dead) or "ok")
        failures += dead

        try:
            order, titles, stack = stack_churn.read_stack(base_commit,
                                                          head_start)
            pairs, added_counts = stack_churn.churn(stack)
            counts = stack_churn.totals(pairs, titles)
            text = stack_churn.report(pairs, added_counts, titles, order,
                                      churn_limit)
            section("Stack churn", text or "none: no commit removes a line "
                    "an earlier commit of the stack added")
            for change in order:
                if counts.get(change, 0) >= churn_limit:
                    failures.append(
                        "%s removes %d lines that earlier commits of the "
                        "stack added (limit %d): fold each edit into the "
                        "commit that introduced the lines, or re-cut the "
                        "stack" % (change, counts[change], churn_limit))
        except stack_churn.NotLinear as exc:
            section("Stack churn", "not checked: %s. Read the stack as one "
                    "diff instead." % exc)

        added = kit.added_lines(kit.range_diff(base_commit, head_start))
        reads, invariants = [], []
        for path, lines in sorted(added.items()):
            if not kit.is_cpp(path) or kit.is_test_path(path):
                continue
            text = kit.file_text(head_start, path)
            if text is None:
                continue
            found_reads, found_invariants = kit.map_index_problems(
                path, text, set(lines))
            reads += found_reads
            invariants += found_invariants
        body = []
        if reads:
            body.append("operator[] reads:\n" + "\n".join(reads))
            failures.append("read through a map's operator[], which inserts "
                            "on a miss: use find(), or at() where the key "
                            "always exists: " + ", ".join(reads))
        if invariants:
            body.append("loop-invariant lookups (hoist each, unless the loop "
                        "inserts into the map; not blocking):\n"
                        + "\n".join(invariants))
        section("C++ map lookups", "\n\n".join(body) or "ok")

        body = "\n".join(
            "WARNING (not blocking): %s touches %s and has no 'Production "
            "impact' block or 'Production impact: none (<why>)' line "
            "(lenses/common/change_hygiene.md section 3)"
            % (commit[:12], ", ".join(touched))
            for commit, touched in _missing_impact(commits))
        body = body or "ok"
        section("Production impact (not blocking)", body)

        run_commands(top, files, added, failures)

        if kit.config("reviewCmd").strip():
            corpus = kit.stack_corpus(base_commit, head_start)
            notes = []
            for commit in commits:
                short, fp = commit[:12], fingerprints[commit]
                path = os.path.join(state, "reviews", fp + ".md")
                problem = kit.saved_report_problem(path, fp)
                if problem == "missing":
                    failures.append("%s: no AI review for this message and "
                                    "patch (%s missing): run local_review.py"
                                    % (short, path))
                    continue
                if problem:
                    failures.append("%s: review report %s is %s: run "
                                    "local_review.py (it replaces the file)"
                                    % (short, path, problem))
                    continue
                with open(path, encoding="utf-8", errors="replace") as fh:
                    report = fh.read()
                open_ids = kit.open_findings(report)
                if open_ids:
                    failures.append("%s: review report %s has open findings "
                                    "%s: fix them and re-run local_review.py,"
                                    " or move each under '## Declined' with "
                                    "the reason" % (short, path,
                                                    ", ".join(open_ids)))
                for problem in declined_problems(report, corpus):
                    failures.append("%s: review report %s: %s"
                                    % (short, path, problem))
                notes.append("%s: %s" % (short, path))
            section("AI review", "\n".join(notes) or "no usable report")
        else:
            section("AI review", "NOTE: no reviewCmd configured; the AI "
                    "review pass was skipped")
    except kit.KitError as exc:
        failures.append("a check could not run (%s); re-run" % exc)

    print("\n######## Gate")
    try:
        head_end = kit.rev_parse("HEAD")
    except kit.KitError:
        head_end = None
    if head_end != head_start:
        failures.append("HEAD moved while the gate ran (%s -> %s): re-run it"
                        % (head_start[:12], (head_end or "?")[:12]))
    if failures:
        for failure in failures:
            print("FAIL: %s" % failure)
        print("Push blocked.")
        return 1
    stamp = {
        "time": int(time.time()),
        "base": base_ref,
        "base_commit": base_commit,
        "head": head_start,
        "commits": {c: fingerprints[c] for c in commits},
        "truth_audit_overrides": overrides_used,
    }
    path = os.path.join(state, "gate_pass", stamp_key(commits) + ".json")
    kit.write_atomic(path, json.dumps(stamp, indent=1, sort_keys=True) + "\n")
    print("PASS on the mechanical checks, recorded in %s. The pre-push hook "
          "accepts these commits for 7 days while their fingerprints stay "
          "the same." % path)
    print("Still to do by hand: verify the manual checklist each truth audit "
          "printed above, sentence by sentence.")
    return 0


def published_history():
    """(rev-list arguments naming history that needs no gate pass, whether
    this is the repository's first push)."""
    # Commits a remote already has are published, whoever wrote them: a fork
    # workflow fetches the mainline from one remote and pushes to another.
    if kit.git("for-each-ref", "--count=1", "refs/remotes").strip():
        return ["--remotes"], False
    # Before anything was pushed or fetched there is no mainline to measure
    # a stack from, so gate.py cannot stamp the base branch's own commits
    # and its first push could never pass.
    return [kit.resolve_base()], True


def check_push(remote_name, stdin_text):
    """Exit code of the pre-push check for git's stdin lines."""
    try:
        pushed = []
        published = None
        for line in stdin_text.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            local_ref, local_hash = parts[0], parts[1]
            if (not local_ref.startswith("refs/heads/")
                    or ZERO_HASH.match(local_hash)):
                continue
            if published is None:
                published, first_push = published_history()
                if first_push:
                    print("review-kit pre-push: first push (to %s): no "
                          "remote-tracking branch exists yet, so commits on "
                          "%s are not checked." % (remote_name, published[0]))
            out = kit.git("rev-list", "--no-merges", local_hash, "--not",
                          *published)
            for commit in out.split():
                if commit not in pushed:
                    pushed.append(commit)
        if not pushed:
            return 0
        state = kit.state_dir()
        fps = {c: kit.fingerprint_of(c) for c in pushed}
        msg_problems = {}
        for commit in pushed:
            problems = kit.message_problems(kit.message(commit))
            if problems:
                msg_problems[commit] = problems
    except kit.KitError as exc:
        print("review-kit pre-push: cannot check the push: %s" % exc)
        return 1
    stamps = load_stamps(state)
    wanted = set(fps.values())
    covered = any(wanted <= set((s.get("commits") or {}).values())
                  for s in stamps)
    if covered and not msg_problems:
        return 0
    stamped = set()
    for stamp in stamps:
        stamped |= set((stamp.get("commits") or {}).values())
    print("review-kit pre-push: push blocked.")
    if not covered:
        missing = [c for c in pushed if fps[c] not in stamped]
        if missing:
            print("No gate pass from the last 7 days covers these commits:")
            for commit in missing:
                print("  %s %s" % (commit[:12],
                                   kit.subject(kit.message(commit))))
        else:
            print("Each commit was gated, but no single gate pass covers "
                  "all of them; gate the whole stack at once.")
    for commit, problems in msg_problems.items():
        for problem in problems:
            print("  %s: %s" % (commit[:12], problem))
    print("Run %s from the branch you push, fix what it reports, and push "
          "again." % os.path.join(kit.SCRIPTS_DIR, "gate.py"))
    return 1


def main(argv):
    parser = argparse.ArgumentParser(
        description="Pre-push gate over merge-base..HEAD.")
    parser.add_argument("--base",
                        help="mainline ref (default: reviewkit.base)")
    parser.add_argument("--check-push", nargs=2,
                        metavar=("REMOTE_NAME", "REMOTE_URL"))
    args = parser.parse_args(argv)
    if args.check_push:
        return check_push(args.check_push[0], sys.stdin.read())
    try:
        return run_gate(args.base)
    except subprocess.SubprocessError as exc:
        print("gate: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
