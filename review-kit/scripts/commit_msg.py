#!/usr/bin/env python3
"""Commit message checks, for git's commit-msg hook or a manual run.

Usage:
  commit_msg.py MSGFILE

Lines starting with '#' and everything from git's scissors line on are
ignored, as git does when it stores the message. The rules are in
kit.message_problems: a non-empty subject, no match of reviewkit.forbidMessage
(tool or AI attribution by default), no paragraph or line over 30 characters
repeated, and every trailer named in reviewkit.requireTrailers.

Exit codes:
  0  the message passes
  1  at least one problem, printed one per line
  2  the file could not be read, or a setting is invalid
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: commit_msg.py MSGFILE", file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8", errors="replace") as handle:
            text = kit.clean_message(handle.read())
    except OSError as exc:
        print("commit_msg: cannot read %s: %s" % (argv[0], exc),
              file=sys.stderr)
        return 2
    problems = kit.message_problems(text)
    for problem in problems:
        print("commit-msg: %s" % problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
