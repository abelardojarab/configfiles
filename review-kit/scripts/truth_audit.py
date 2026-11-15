#!/usr/bin/env python3
"""Truth audit of one commit: its message and the comments it adds.

Usage:
  truth_audit.py [REV] [--base B]

REV defaults to HEAD; B defaults to reviewkit.base. The sources are the
message body lines and the comment text on lines the commit adds (all added
text in Markdown). What can be checked mechanically is flagged:

  [attribution]  the message matches reviewkit.forbidMessage
  [symbol]       a code-looking name in the message or in a source-code
                 comment that is found neither in the code of the files the
                 stack touches nor anywhere in the tree at the merge base.
                 Lines of prose files (Markdown, YAML, TOML, Dockerfiles and
                 the like) only reach the checklist: their capitalized words
                 are products and settings, not symbols. A name listed in
                 reviewkit.knownNames is never flagged.
  [commit]       a commit hash that does not exist, or that is neither merged
                 nor in the stack while the sentence does not say pending,
                 unmerged or parent
  [config]       a `name = value` claim in the message whose name is not in
                 the tree at REV
  [dup]          a paragraph or line repeated in the message

Issue references are printed for a look, not flagged. Then every source
sentence is printed as a numbered checklist to verify by hand. The output
format is parsed by gate.py: a line `== Flags`, the flags or `(none)`, a line
starting `== Manual checklist`, then `NNN. [where] text` lines.

Exit codes:
  0  no flags
  1  at least one flag
  2  the commit or the repository could not be read
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

# Words that look like code by the token rule but name no symbol.
SKIP_TOKENS = {"TODO", "FIXME", "NOTE", "LGTM", "HACK", "GitHub", "GitLab",
               "JavaScript", "TypeScript", "PostgreSQL", "MySQL", "SQLite",
               "MacOS", "OpenAPI", "OAuth", "WebSocket", "PowerShell", "LaTeX",
               "NumPy", "PyPI", "DevOps", "YouTube", "LinkedIn", "iPhone"}
NO_LINTER_PREFIXES = ("NOLINT", "noqa", "pylint:", "type: ignore",
                      "eslint-disable", "clang-format", "keep-sorted")
URL = re.compile(r"\b(?:https?|ftp|file)://\S+")
HEX_REF = re.compile(r"(?<![-\w./])[0-9a-f]{7,40}(?![-\w])")
KNOB = re.compile(
    r"\b([a-z][a-z0-9]*_[a-z0-9_]+)\s*=\s*(?:True|False|true|false|\d)")
PENDING_WORDS = re.compile(r"\b(?:pending|unmerged|parent)\b", re.I)


def tokens(text):
    """Code-looking names in `text`: backticked text, CamelCase, and
    UPPER_SNAKE with at least two underscores; the last `::` component of
    each, longer than 3 characters."""
    text = URL.sub("", text)
    found = set(re.findall(r"`([^`]+)`", text))
    found |= set(re.findall(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b", text))
    found |= set(re.findall(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){2,}\b", text))
    idents = set()
    for tok in found:
        for ident in re.findall(
                r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*", tok):
            last = ident.split("::")[-1]
            if (len(last) > 3 and last not in SKIP_TOKENS
                    and ("_" in last or re.search(r"[a-z][A-Z]", last)
                         or last.isupper())):
                idents.add(last)
    return idents


def added_comment_lines(diff):
    """[(path, text)] for comment text on lines the diff adds; every
    non-blank added line of a Markdown file."""
    out = []
    for path, lines in kit.added_lines(diff).items():
        for _, text in sorted(lines.items()):
            if kit.is_markdown(path):
                if text.strip():
                    out.append((path, text.strip()))
                continue
            comment = kit.comment_text(path, text)
            if comment and not comment.startswith(NO_LINTER_PREFIXES):
                out.append((path, comment))
    return out


def audit(rev, base_commit):
    """(flags, issue lines, sources) for commit `rev`."""
    msg = kit.message(rev)
    body, _ = kit.split_message(msg)
    body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    sources = ([("message", line) for line in body_lines]
               + added_comment_lines(kit.commit_diff(rev)))
    flags = []

    try:
        regex = kit.forbid_regex()
    except kit.KitError as exc:
        flags.append("[attribution] %s" % exc)
        regex = None
    for line in kit.forbidden_lines(msg, regex):
        flags.append("[attribution] the message matches "
                     "reviewkit.forbidMessage: %s" % line)

    corpus = kit.stack_corpus(base_commit, rev)
    checked = {}
    known = kit.known_names()
    for where, text in sources:
        if where != "message" and kit.is_prose(where):
            continue
        for tok in sorted(tokens(text)):
            if tok in checked or tok in known:
                continue
            # An all-caps name is often the end of a longer constant, such as
            # an enum value written without its type prefix.
            suffix = tok.isupper()
            ok = (kit.has_word(tok, corpus, suffix=suffix)
                  or kit.tree_has_word(base_commit, tok, suffix=suffix))
            checked[tok] = ok
            if not ok:
                flags.append("[symbol] `%s` (%s) exists neither in the "
                             "stack's code at %s nor in the tree at the merge "
                             "base %s: stale name?"
                             % (tok, where, rev[:12], base_commit[:12]))

    stack = set(kit.stack_commits(base_commit, rev))
    for where, text in sources:
        for ref in sorted(set(HEX_REF.findall(text))):
            if not (re.search(r"[0-9]", ref) and re.search(r"[a-f]", ref)):
                continue
            code, out, _ = kit.run_git(["rev-parse", "--verify", "--quiet",
                                        ref + "^{commit}"])
            if code != 0 or not out.strip():
                flags.append("[commit] %s (%s) names no commit in this "
                             "repository" % (ref, where))
                continue
            commit = out.strip()
            if commit in stack or kit.is_ancestor(commit, base_commit):
                continue
            if not PENDING_WORDS.search(text):
                flags.append("[commit] %s (%s) is neither merged nor in this "
                             "stack, but the sentence does not say pending, "
                             "unmerged or parent: %s"
                             % (ref, where, text[:100]))

    for where, text in sources[:len(body_lines)]:
        for knob in sorted(set(KNOB.findall(URL.sub("", text)))):
            if not kit.tree_has_word(rev, knob):
                flags.append("[config] `%s` (%s) is not in the tree at %s: "
                             "say which unmerged change sets it"
                             % (knob, where, rev[:12]))

    for item in kit.repeated_text(msg):
        flags.append("[dup] repeated in the message: %s" % item[:90])

    issues = []
    for where, text in sources:
        for ref in kit.issue_refs(text):
            line = "[issue] %s (%s) <- matches this change?" % (ref, where)
            if line not in issues:
                issues.append(line)
    return list(dict.fromkeys(flags)), issues, sources


def render(flags, issues, sources):
    out = list(issues)
    out.append("")
    out.append("== Flags")
    out.extend(flags or ["(none)"])
    out.append("")
    out.append("== Manual checklist: mark each line true at this commit and "
               "at its place in the stack, or fix it")
    for number, (where, text) in enumerate(sources, 1):
        out.append("%3d. [%s] %s" % (number, where, text))
    return "\n".join(out)


def main(argv):
    parser = argparse.ArgumentParser(
        description="Truth audit of one commit's message and comments.")
    parser.add_argument("rev", nargs="?", default="HEAD")
    parser.add_argument("--base",
                        help="mainline ref (default: reviewkit.base)")
    args = parser.parse_args(argv)
    try:
        rev = kit.rev_parse(args.rev)
        base_commit = kit.merge_base(kit.resolve_base(args.base), rev)
        flags, issues, sources = audit(rev, base_commit)
    except kit.KitError as exc:
        print("truth_audit: %s" % exc, file=sys.stderr)
        return 2
    print(render(flags, issues, sources))
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
