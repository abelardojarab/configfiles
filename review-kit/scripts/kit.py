#!/usr/bin/env python3
"""Shared helpers for the review-kit scripts: git, settings, diff parsing,
fingerprints, commit message rules, review reports and the state directory.

The other scripts import this module. Run directly, it prints the settings it
resolves for the repository in the current directory, which helps when a
setting seems to be ignored.

Usage:
  kit.py

Exit codes:
  0  settings printed
  2  not inside a git work tree, or a setting is invalid
"""
import collections
import functools
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
KIT_DIR = os.path.dirname(SCRIPTS_DIR)

# Forced on every git call so user configuration cannot change what the
# parsers below read: quoted non-ASCII paths, color codes, or paths relative
# to the current directory.
GIT = ["git", "-c", "core.quotePath=false", "-c", "color.ui=false",
       "-c", "diff.relative=false"]
DIFF_FLAGS = ["--no-color", "--no-ext-diff", "--no-textconv",
              "--src-prefix=a/", "--dst-prefix=b/", "-M"]
AUTO_BASES = ("origin/HEAD", "origin/main", "origin/master", "main", "master")

_AI_TOOLS = (r"claude|copilot|gemini|gpt|chatgpt|openai|anthropic|cursor"
             r"|codex|aider|devin")
# Two of the tool names are also given names, so for those a co-author
# trailer counts only with a qualifier that a person's name does not carry,
# or with no surname at all before the address.
DEFAULT_FORBID_MESSAGE = (
    r"^[ \t]*co-authored-by[ \t]*:[^\n]*(?:"
    r"\b(?:copilot|gemini|gpt|chatgpt|openai|anthropic|cursor|codex|aider)\b"
    r"|\bclaude(?:[ \t]+(?:code|opus|sonnet|haiku|ai)\b|\.ai\b|\[bot\])"
    r"|\bdevin(?:[- ]ai\b|\.ai\b|\[bot\])"
    # A person signs with a surname; a bare "Claude <mail>" is the model.
    r"|\b(?:claude|devin)[ \t]*<)"
    r"|^[^\n]*\bgenerated[ \t]+(?:with|by)\b[^\n]*\b(?:"
    + _AI_TOOLS + r"|ai)\b"
    r"|^[ \t]*(?:assisted-by|ai-assisted)[ \t]*:"
    r"|\U0001F916")

DEFAULTS = {
    "base": "auto",
    "maxLines": "150",
    "maxCols": "80",
    "churnLimit": "5",
    "forbidMessage": DEFAULT_FORBID_MESSAGE,
    "requireTrailers": "",
    "knownNames": "",
    "lenses": "auto",
    "reviewCmd": "",
    "verifyCmd": "",
    "stateDir": "",
}

# A commit that only relocates existing code or regenerates golden files is
# large by nature, and later commits are expected to edit what it moved.
MOVE_ONLY = re.compile(r"pure move|golden", re.I)
DUP_MIN_CHARS = 30
MIN_REASON_CHARS = 20
MIN_REPORT_CHARS = 400
PROVENANCE = "<!-- local_review.py commit={commit} fingerprint={fp} -->"
PROVENANCE_RE = re.compile(
    r"^<!-- local_review\.py commit=([0-9a-f]{12}) "
    r"fingerprint=([0-9a-f]{12}) -->$")

C_FAMILY_EXT = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp",
                ".hxx", ".h++", ".inl", ".m", ".mm", ".cu", ".cuh"}
CPP_EXT = C_FAMILY_EXT - {".c", ".m"}
CUDA_EXT = {".cu", ".cuh"}
HEADER_EXT = {".h", ".hh", ".hpp", ".hxx", ".h++", ".cuh"}
SLASH_EXT = C_FAMILY_EXT | {
    ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".go", ".rs", ".kt", ".kts", ".swift", ".proto"}
HASH_EXT = {".py", ".pyi", ".sh", ".bash", ".zsh", ".ksh", ".rb", ".yaml",
            ".yml", ".toml", ".cmake", ".bzl", ".star", ".mk"}
HASH_NAMES = {"CMakeLists.txt", "BUILD", "BUILD.bazel", "WORKSPACE",
              "WORKSPACE.bazel", "MODULE.bazel", "Makefile", "makefile",
              "GNUmakefile", "Dockerfile", "Containerfile", "Rakefile",
              "Gemfile"}
DASH_EXT = {".sql", ".lua"}
SEMI_EXT = {".el", ".lisp", ".lsp", ".scm", ".ss", ".rkt", ".clj", ".cljs",
            ".cljc", ".edn", ".fnl"}
MARKDOWN_EXT = {".md", ".markdown"}
# Files whose comments describe products, services and settings rather than
# code: the truth audit lists their lines for a manual look but does not
# treat a capitalized word in them as a symbol.
PROSE_EXT = MARKDOWN_EXT | {".txt", ".rst", ".yaml", ".yml", ".toml", ".ini",
                            ".cfg", ".conf", ".json", ".env", ".service",
                            ".timer", ".socket"}
PROSE_NAMES = {"Dockerfile", "Containerfile"}
TEST_PATH = re.compile(r"_test\.|(?:^|/)test_|\.test\.|_spec\.|(?:^|/)tests?/")

# Standards that are written NAME-number and are not issue keys.
_NOT_ISSUE_PREFIXES = {"AES", "ANSI", "CRC", "CVE", "ECMA", "ES",
                       "HTTP", "IEEE", "IPV", "ISO", "MD", "PEP", "RFC", "RSA",
                       "SHA", "SSL", "TLS", "UCS", "UTF", "X"}
_ISSUE_RE = re.compile(
    r"(?<![\w&/#])#\d+\b|\b[A-Z][A-Z0-9]+-\d+\b|\bissues/\d+\b")


class KitError(RuntimeError):
    """A setting, a ref or the repository could not be used."""


class GitError(KitError):
    """A git command failed."""


# ---------------------------------------------------------------- git

def run_git(args, cwd=None, input_text=None):
    """Returns (exit code, stdout, stderr) of one git command."""
    proc = subprocess.run(
        GIT + list(args), cwd=cwd or _work_dir(), input=input_text,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


def git(*args, cwd=None, input_text=None):
    """Returns stdout of a git command; raises GitError when it fails."""
    code, out, err = run_git(args, cwd=cwd, input_text=input_text)
    if code != 0:
        raise GitError("git %s failed: %s" % (" ".join(args),
                                              err.strip()[-400:]))
    return out


@functools.lru_cache(maxsize=None)
def _toplevel(cwd):
    proc = subprocess.run(GIT + ["rev-parse", "--show-toplevel"], cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace")
    top = proc.stdout.rstrip("\n")
    if proc.returncode != 0 or not top:
        raise GitError("not inside a git work tree (%s)" % cwd)
    return top


def root():
    """Top of the work tree that holds the current directory."""
    return _toplevel(os.getcwd())


def _work_dir():
    # Paths in `rev:path` and git grep are resolved against the work tree
    # top, so every command runs there; outside a repository (a message file
    # checked on its own) the current directory is the only choice.
    try:
        return root()
    except GitError:
        return os.getcwd()


def rev_parse(rev):
    """Full hash of the commit `rev` names; raises GitError if none."""
    code, out, _ = run_git(["rev-parse", "--verify", "--quiet",
                            rev + "^{commit}"])
    if code != 0 or not out.strip():
        raise GitError("%s does not name a commit" % rev)
    return out.strip()


def resolve_base(cli_value=None):
    """The mainline ref: the argument, else reviewkit.base, else the first of
    AUTO_BASES that exists."""
    wanted = cli_value or config("base") or "auto"
    candidates = AUTO_BASES if wanted == "auto" else (wanted,)
    for ref in candidates:
        code, _, _ = run_git(["rev-parse", "--verify", "--quiet",
                              ref + "^{commit}"])
        if code == 0:
            return ref
    raise KitError("no base ref found (tried %s); set one with "
                   "git config reviewkit.base <ref> or --base"
                   % ", ".join(candidates))


def merge_base(base, rev="HEAD"):
    code, out, err = run_git(["merge-base", base, rev])
    if code != 0 or not out.strip():
        raise GitError("%s and %s have no merge base %s"
                       % (base, rev, err.strip()[-200:]))
    return out.strip()


def stack_commits(base_commit, head="HEAD"):
    """Commits of base_commit..head, oldest first, merges excluded."""
    return git("rev-list", "--reverse", "--topo-order", "--no-merges",
               "%s..%s" % (base_commit, head)).split()


def merge_commits(base_commit, head="HEAD"):
    return git("rev-list", "--merges",
               "%s..%s" % (base_commit, head)).split()


def is_ancestor(commit, of):
    code, _, _ = run_git(["merge-base", "--is-ancestor", commit, of])
    return code == 0


def message(rev):
    """The raw commit message. Read from the object, so log settings such as
    showSignature cannot add lines to it."""
    raw = git("cat-file", "commit", rev_parse(rev))
    return raw.partition("\n\n")[2]


def subject(text):
    stripped = text.strip()
    return stripped.splitlines()[0] if stripped else ""


def commit_diff(rev):
    return git("diff-tree", "-p", "-r", "--root", "--no-commit-id",
               *DIFF_FLAGS, rev)


def range_diff(old, new):
    return git("diff", *DIFF_FLAGS, old, new, "--")


def staged_diff():
    return git("diff", "--cached", *DIFF_FLAGS, "--")


def changed_files(old, new):
    """Paths that exist at `new` and differ between the two commits."""
    out = git("diff", "--name-only", "-z", "--no-ext-diff", "-M",
              "--diff-filter=d", old, new, "--")
    return [name for name in out.split("\0") if name]


def file_text(rev, path):
    """Contents of `path` at `rev` (None: the index), or None if absent."""
    spec = (":" if rev is None else rev + ":") + path
    code, out, _ = run_git(["cat-file", "blob", spec])
    return out if code == 0 else None


def tree_has_word(rev, word, suffix=False):
    """Whether `word` (an identifier) appears in the tree at `rev`. With
    `suffix`, the end of a longer identifier counts too."""
    if suffix:
        args = ["grep", "-q", "-I", "--no-color", "-E", "-e",
                word + "([^A-Za-z0-9_]|$)", rev, "--"]
    else:
        args = ["grep", "-q", "-I", "--no-color", "-w", "-F", "-e", word,
                rev, "--"]
    code, _, err = run_git(args)
    if code > 1:
        raise GitError("git grep failed: %s" % err.strip()[-200:])
    return code == 0


# ---------------------------------------------------------------- settings

def env_name(key):
    """reviewkit.maxLines -> REVIEWKIT_MAX_LINES."""
    return "REVIEWKIT_" + re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key).upper()


def config(key):
    """A setting: the environment override, else git config, else default."""
    value = os.environ.get(env_name(key))
    if value is not None:
        return value
    code, out, _ = run_git(["config", "--get", "reviewkit." + key])
    if code == 0:
        return out.rstrip("\n")
    return DEFAULTS.get(key, "")


def config_all(key):
    """A multi-valued setting. The environment override holds one value per
    line."""
    value = os.environ.get(env_name(key))
    if value is not None:
        return [line for line in value.splitlines() if line.strip()]
    code, out, _ = run_git(["config", "--get-all", "reviewkit." + key])
    if code != 0:
        return []
    return [line for line in out.splitlines() if line.strip()]


def config_int(key):
    value = config(key)
    try:
        return int(value)
    except ValueError:
        raise KitError("reviewkit.%s must be an integer, got %r"
                       % (key, value))


def home_dir():
    """Directory holding prompts/ and lenses/: REVIEWKIT_HOME when it names a
    directory, else the kit this script belongs to."""
    override = os.environ.get("REVIEWKIT_HOME")
    if override and os.path.isdir(override):
        return os.path.abspath(override)
    return KIT_DIR


def _inside(path, parent):
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def state_dir():
    """Where reports, overrides and stamps live. Kept out of the work tree so
    they are never committed or swept up by linters."""
    top = root()
    common = os.path.realpath(
        os.path.join(top, git("rev-parse", "--git-common-dir").strip()))
    configured = config("stateDir")
    if configured:
        path = os.path.realpath(
            os.path.join(top, os.path.expanduser(configured)))
    else:
        path = os.path.join(common, "review-kit")
    if _inside(path, os.path.realpath(top)) and not _inside(path, common):
        raise KitError("stateDir %s is inside the work tree; point "
                       "reviewkit.stateDir somewhere else" % path)
    return path


# ---------------------------------------------------------------- diffs

_C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13,
              '"': 34, "\\": 92}


def unquote_path(text):
    """A path as git prints it in a diff header, unquoted."""
    if text.endswith("\t"):
        # git appends a tab to header paths that contain a space.
        text = text[:-1]
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        return text
    body, raw, pos = text[1:-1], bytearray(), 0
    while pos < len(body):
        char = body[pos]
        if char == "\\" and pos + 1 < len(body):
            nxt = body[pos + 1]
            if nxt in "01234567" and re.match(r"[0-7]{3}", body[pos + 1:]):
                raw.append(int(body[pos + 1:pos + 4], 8))
                pos += 4
                continue
            raw.append(_C_ESCAPES.get(nxt, ord(nxt)))
            pos += 2
            continue
        raw.extend(char.encode("utf-8"))
        pos += 1
    return raw.decode("utf-8", "replace")


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def sections(diff):
    """Yields (old path, new path, hunks) per file of a git-format diff.

    A path is None for /dev/null. Each hunk is (old start, old length, new
    start, new length, lines). Lines are attributed to a hunk by its header's
    lengths, so a removed line that itself starts with "-- " is not read as a
    file header.
    """
    old = new = None
    hunks = []
    old_left = new_left = 0
    started = False
    for line in diff.splitlines():
        if old_left > 0 or new_left > 0:
            hunks[-1][4].append(line)
            if line.startswith("-"):
                old_left -= 1
            elif line.startswith("+"):
                new_left -= 1
            elif not line.startswith("\\"):
                old_left -= 1
                new_left -= 1
            continue
        match = HUNK.match(line)
        if match:
            old_left = int(match.group(2) if match.group(2) is not None
                           else 1)
            new_left = int(match.group(4) if match.group(4) is not None
                           else 1)
            hunks.append((int(match.group(1)), old_left, int(match.group(3)),
                          new_left, []))
        elif line.startswith("diff --git "):
            if started:
                yield old, new, hunks
            old = new = None
            hunks = []
            started = True
        elif line.startswith("rename from "):
            old = unquote_path(line[len("rename from "):])
        elif line.startswith("rename to "):
            new = unquote_path(line[len("rename to "):])
        elif line.startswith("--- "):
            path = unquote_path(line[4:])
            old = None if path == "/dev/null" else re.sub(r"^a/", "", path)
        elif line.startswith("+++ "):
            path = unquote_path(line[4:])
            new = None if path == "/dev/null" else re.sub(r"^b/", "", path)
    if started:
        yield old, new, hunks


def added_lines(diff):
    """{path: {new line number: text}} for the lines the diff adds."""
    added = {}
    for _, new, hunks in sections(diff):
        if new is None:
            continue
        for _, _, new_start, _, lines in hunks:
            line_no = new_start
            for line in lines:
                if line.startswith("+"):
                    added.setdefault(new, {})[line_no] = line[1:]
                    line_no += 1
                elif not line.startswith(("-", "\\")):
                    line_no += 1
    return added


def changed_line_count(diff):
    """Added plus deleted lines."""
    return sum(1 for _, _, hunks in sections(diff) for hunk in hunks
               for line in hunk[4] if line.startswith(("+", "-")))


def patch_lines(diff):
    """{path: [+/- lines]} per file."""
    files = {}
    for old, new, hunks in sections(diff):
        path = new or old
        if path is None:
            continue
        bucket = files.setdefault(path, [])
        for hunk in hunks:
            bucket.extend(line.rstrip() for line in hunk[4]
                          if line.startswith(("+", "-")))
    return files


# ---------------------------------------------------------------- messages

SCISSORS = re.compile(r"^# -+ >8 -+$")


def clean_message(text):
    """A commit message file as git would store it: comment lines and
    everything from the scissors line on removed."""
    kept = []
    for line in text.splitlines():
        if SCISSORS.match(line):
            break
        if line.startswith("#"):
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).strip()


def split_message(text):
    """(body, [(key, value)]): the message without its trailer block, and the
    trailers git recognizes in it."""
    text = text.strip("\n")
    code, out, _ = run_git(["interpret-trailers", "--parse", "--no-divider"],
                           input_text=text + "\n")
    trailers = []
    if code == 0:
        for line in out.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                trailers.append((key.strip(), value.strip()))
    body = text
    if trailers:
        # git takes the trailer block from the last paragraph only.
        paragraphs = re.split(r"\n[ \t]*\n", text.strip())
        if len(paragraphs) > 1:
            body = "\n\n".join(paragraphs[:-1])
    return body, trailers


def message_body(text):
    """The message body, trailers dropped, whitespace-normalized."""
    body, _ = split_message(text)
    lines = [line.strip() for line in body.strip().splitlines()]
    return "\n".join(lines).strip()


def forbid_regex():
    """The compiled reviewkit.forbidMessage, or None when it is empty."""
    pattern = config("forbidMessage")
    if not pattern.strip():
        return None
    try:
        return re.compile(pattern, re.I | re.M)
    except re.error as exc:
        raise KitError("reviewkit.forbidMessage is not a valid regex (%s)"
                       % exc)


def forbidden_lines(text, regex):
    """The lines of `text` where `regex` matches, each once."""
    found = []
    if regex is None:
        return found
    for match in regex.finditer(text):
        start = text.rfind("\n", 0, match.start()) + 1
        end = text.find("\n", match.start())
        line = text[start:len(text) if end < 0 else end].strip()
        if line not in found:
            found.append(line)
    return found


def repeated_text(text):
    """Paragraphs and lines over DUP_MIN_CHARS that appear more than once in
    the message body. Trailers are left out: the same trailer key on several
    lines is normal."""
    text, _ = split_message(text)
    paragraphs = [re.sub(r"\s+", " ", part).strip()
                  for part in re.split(r"\n\s*\n", text)]
    lines = [line.strip() for line in text.splitlines()]
    found = []
    for group in (paragraphs, lines):
        seen = set()
        for item in group:
            if len(item) <= DUP_MIN_CHARS:
                continue
            if item in seen and item not in found:
                found.append(item)
            seen.add(item)
    return found


def message_problems(text):
    """Every commit message rule the message breaks, one line each."""
    problems = []
    if not text.strip():
        problems.append("empty subject: the first line of the message is "
                        "blank")
    try:
        regex = forbid_regex()
    except KitError as exc:
        problems.append(str(exc))
        regex = None
    for line in forbidden_lines(text, regex):
        problems.append("matches reviewkit.forbidMessage (tool or AI "
                        "attribution): %s" % line)
    for item in repeated_text(text):
        problems.append("repeated in the message: %s" % item[:90])
    required = [key.strip() for key in config("requireTrailers").split(",")
                if key.strip()]
    if required:
        _, trailers = split_message(text)
        present = {key.lower() for key, _ in trailers}
        for key in required:
            if key.lower() not in present:
                problems.append("missing trailer %s: (required by "
                                "reviewkit.requireTrailers)" % key)
    return problems


# ---------------------------------------------------------------- fingerprint

def fingerprint(message_text, diff):
    """12 hex characters over the message body and the net patch lines.

    Each file contributes its net added and removed lines as multisets, so
    hunk positions, context and the order git aligns a moved line in do not
    count, and a rebase that leaves body and patch alone keeps the value.
    """
    digest = hashlib.sha256(message_body(message_text).encode("utf-8"))
    for path, lines in sorted(patch_lines(diff).items()):
        added = collections.Counter(l[1:] for l in lines if l.startswith("+"))
        removed = collections.Counter(l[1:] for l in lines
                                      if l.startswith("-"))
        net = sorted(["+" + l for l in (added - removed).elements()]
                     + ["-" + l for l in (removed - added).elements()])
        if net:
            digest.update(("\0" + path + "\n" + "\n".join(net))
                          .encode("utf-8"))
    return digest.hexdigest()[:12]


def fingerprint_of(rev):
    return fingerprint(message(rev), commit_diff(rev))


# ---------------------------------------------------------------- file types

def _ext(path):
    return os.path.splitext(path)[1].lower()


def is_markdown(path):
    return _ext(path) in MARKDOWN_EXT


def is_prose(path):
    """Whether comments in `path` are prose rather than code comments."""
    base = os.path.basename(path)
    return (_ext(path) in PROSE_EXT or base in PROSE_NAMES
            or base.startswith(("Dockerfile.", "Containerfile.")))


def known_names():
    """Names reviewkit.knownNames lists as real although no code defines
    them (product names, services, config keys)."""
    return {name.strip() for name in config("knownNames").split(",")
            if name.strip()}


def is_c_family(path):
    return _ext(path) in C_FAMILY_EXT


def is_cpp(path):
    return _ext(path) in CPP_EXT


def is_header(path):
    return _ext(path) in HEADER_EXT


def is_test_path(path):
    return TEST_PATH.search(path) is not None


def comment_marker(path):
    """The line comment marker for the file type, or None."""
    base, ext = os.path.basename(path), _ext(path)
    if ext in SLASH_EXT:
        return "//"
    if (ext in HASH_EXT or base in HASH_NAMES
            or base.startswith(("Dockerfile.", "Containerfile."))):
        return "#"
    if ext in DASH_EXT:
        return "--"
    if ext in SEMI_EXT:
        return ";"
    return None


def split_comment(path, line):
    """(code, comment) of one line; comment is None when there is none."""
    marker = comment_marker(path)
    if marker is None:
        return line, None
    pos = 0
    while True:
        pos = line.find(marker, pos)
        if pos < 0:
            return line, None
        if marker == "//" and pos > 0 and line[pos - 1] == ":":
            pos += 2  # a URL, not a comment
            continue
        return line[:pos], line[pos + len(marker):]


def comment_text(path, line):
    """The comment on a line with its marker run stripped, or None."""
    _, comment = split_comment(path, line)
    if comment is None:
        return None
    return comment.lstrip(comment_marker(path)[0]).strip()


def stack_corpus(base_commit, rev):
    """Non-comment code of the files base_commit..rev touches, as they are
    at `rev`, plus their base names. Comments are left out so a stale name
    is not found in the comment that cites it."""
    files = changed_files(base_commit, rev)
    parts = [os.path.splitext(os.path.basename(path))[0] for path in files]
    for path in files:
        if is_markdown(path):
            continue
        text = file_text(rev, path)
        if text is not None:
            parts.extend(split_comment(path, line)[0]
                         for line in text.splitlines())
    return "\n".join(parts)


def has_word(word, text, suffix=False):
    left = "" if suffix else r"(?<![A-Za-z0-9_])"
    return re.search(left + re.escape(word) + r"(?![A-Za-z0-9_])",
                     text) is not None


def issue_refs(text):
    """Issue references in `text`: #123, ABC-123, issues/123."""
    refs = []
    for match in _ISSUE_RE.finditer(text):
        ref = match.group(0)
        if "-" in ref and ref.split("-")[0] in _NOT_ISSUE_PREFIXES:
            continue
        refs.append(ref)
    return refs


# ---------------------------------------------------------------- lenses

# Which language lens a file falls under. A lone header is read as C++, the
# more common case; a stack with .c files gets the C lens as well. CUDA
# sources are C++ with device code on top, so they take both lenses.
LENS_EXT = {".c": "c", ".proto": "protobuf", ".py": "python",
            ".pyi": "python", ".ts": "typescript", ".tsx": "typescript",
            ".mts": "typescript", ".cts": "typescript", ".go": "go"}
LENS_NAMES = ("common", "c", "cpp", "cuda", "go", "kernel", "protobuf",
              "python", "typescript")
KERNEL_MARKERS = ("Kconfig", "MAINTAINERS")


def kernel_tree(top):
    """Whether `top` is a Linux kernel tree (it carries Kconfig and
    MAINTAINERS at its root)."""
    return all(os.path.isfile(os.path.join(top, name))
               for name in KERNEL_MARKERS)


def lenses_for(paths, top=None):
    """The lens directories a change needs: `common`, plus the language
    lenses reviewkit.lenses names, or, when it is `auto`, the languages the
    files in `paths` are written in. In a kernel tree (`top`, default the
    current repository) C files take the `kernel` lens too."""
    wanted = config("lenses").strip() or "auto"
    if wanted != "auto":
        chosen = [name.strip() for name in wanted.split(",") if name.strip()]
    else:
        chosen = []
        if top is None:
            try:
                top = root()
            except GitError:
                top = None
        kernel = top is not None and kernel_tree(top)
        for path in paths:
            ext = _ext(path)
            names = []
            if ext in CUDA_EXT:
                names = ["cpp", "cuda"]
            elif ext in CPP_EXT:
                names = ["cpp"]
            elif ext in LENS_EXT:
                names = [LENS_EXT[ext]]
            if kernel and ext in C_FAMILY_EXT:
                names = ["c", "kernel"]
            for name in names:
                if name not in chosen:
                    chosen.append(name)
    out = ["common"]
    for name in chosen:
        if name not in out:
            out.append(name)
    return out


# ---------------------------------------------------------------- C++ maps

# Associative containers whose operator[] inserts a default value on a miss.
MAP_DECL = re.compile(
    r"\b(?:absl::(?:flat|node)_hash_map|absl::btree_map"
    r"|std::(?:unordered_)?map)\s*<")


def map_names(text):
    """Names declared with a map type in `text` (variables, members,
    parameters)."""
    names = set()
    for match in MAP_DECL.finditer(text):
        pos, depth = match.end(), 1
        while pos < len(text) and depth:
            depth += {"<": 1, ">": -1}.get(text[pos], 0)
            pos += 1
        declared = re.match(r"\s*&?\s*(\w+)\s*[;={(,)]", text[pos:pos + 200])
        if declared:
            names.add(declared.group(1))
    return names


def statement_at(lines, idx):
    """The statement around 0-based line `idx`, joined onto one line."""
    start = idx
    while start > 0 and not lines[start - 1].rstrip().endswith(
            (";", "{", "}")):
        start -= 1
    end = idx
    while end < len(lines) - 1 and not lines[end].rstrip().endswith(
            (";", "{", "}")):
        end += 1
    return " ".join(line.strip() for line in lines[start:end + 1])


def enclosing_loop(lines, idx):
    """(header, body lines) of the innermost for loop around `idx`, found by
    indentation; (None, []) outside a loop."""
    indent = len(lines[idx]) - len(lines[idx].lstrip())
    for pos in range(idx - 1, -1, -1):
        text = lines[pos]
        if not text.strip():
            continue
        pos_indent = len(text) - len(text.lstrip())
        if pos_indent < indent:
            if re.match(r"\s*for\s*\(", text):
                return statement_at(lines, pos), lines[pos + 1:idx]
            indent = pos_indent
    return None, []


def map_index_problems(path, text, added_line_nos):
    """(reads, invariants) on the given lines of a C++ file: reads through a
    map's operator[], and map lookups whose key the enclosing loop never
    changes."""
    reads, invariants = [], []
    lines = text.splitlines()
    for name in sorted(map_names(text)):
        index = re.compile(r"\b" + name + r"\s*\[([^\]]*)\]")
        for line_no in sorted(added_line_nos):
            if line_no - 1 >= len(lines):
                continue
            found = index.search(lines[line_no - 1])
            if not found:
                continue
            stmt = statement_at(lines, line_no - 1)
            if (re.search(r"^const\b[^;]*?&\s*\w+\s*=\s*" + name + r"\s*\[",
                          stmt)
                    or re.search(r"\b" + name + r"\s*\[[^\]]*\]\s*\.\s*"
                                 r"(?:contains|find|count|size|empty|at"
                                 r"|begin|end)\s*\(", stmt)
                    or re.search(r"\bfor\s*\([^;]*:\s*" + name + r"\s*\[",
                                 stmt)
                    or re.search(r"\breturn\s+" + name + r"\s*\[", stmt)):
                reads.append("%s:%d %s[...]" % (path, line_no, name))
            header, body = enclosing_loop(lines, line_no - 1)
            if not header:
                continue
            key_ids = set(re.findall(r"[A-Za-z_]\w*", found.group(1)))
            loop_ids = set(re.findall(r"[A-Za-z_]\w*", header.split(":")[0]))
            body_ids = {ident for ident in key_ids for line in body
                        if re.search(r"\b" + ident + r"\s*[{=]|\w[\w:<>]*\s+&?"
                                     + ident + r"\s*[,;)]", line)}
            if key_ids and not key_ids & (loop_ids | body_ids):
                invariants.append("%s:%d %s[%s]" % (path, line_no, name,
                                                    found.group(1)))
    return reads, invariants


# ---------------------------------------------------------------- reports

def provenance_line(short_commit, fp):
    return PROVENANCE.format(commit=short_commit, fp=fp)


def report_problem(text, fp):
    """Why a saved review report cannot be trusted, or None if it can. The
    commit in the provenance line is informational: a rebase that keeps the
    fingerprint keeps the report."""
    first = text.splitlines()[0].strip() if text.strip() else ""
    match = PROVENANCE_RE.match(first)
    if not match or match.group(2) != fp:
        return ("not written by local_review.py (the first line must be "
                "'<!-- local_review.py commit=<sha12> fingerprint=%s -->'); "
                "never write a report by hand" % fp)
    if len(text) < MIN_REPORT_CHARS:
        return ("only %d characters; a real report lists what was checked"
                % len(text))
    return None


def saved_report_problem(path, fp):
    """report_problem() for the file at `path`, or 'missing'."""
    if not os.path.exists(path):
        return "missing"
    with open(path, encoding="utf-8", errors="replace") as handle:
        return report_problem(handle.read(), fp)


def open_findings(report_text):
    """High and Medium findings left open: `### H1 ...` and `### M1 ...`
    headings outside a `## Declined` section."""
    open_ids, declined = [], False
    for line in report_text.splitlines():
        if line.startswith("## "):
            declined = line.lower().startswith("## declined")
        match = re.match(r"^### ([HM]\d+)\b", line)
        if match and not declined:
            open_ids.append(match.group(1))
    return open_ids


_DECLINED_REASON = re.compile(
    r"(?:\*\*Declined[^*]*\*\*:?\s*|Declined[^:\n]*:\s*)(.+)", re.S | re.I)


def _reason_in(lines):
    match = _DECLINED_REASON.search("\n".join(lines))
    return match.group(1).strip() if match else None


def declined_reasons(report_text):
    """{finding id: reason} from the `## Declined` sections of a report."""
    reasons, cur_id, cur_lines, declined = {}, None, [], False

    def close():
        if cur_id is not None and cur_id not in reasons:
            reason = _reason_in(cur_lines)
            if reason:
                reasons[cur_id] = reason

    for line in report_text.splitlines():
        if line.startswith("## "):
            close()
            cur_id, cur_lines = None, []
            declined = line.lower().startswith("## declined")
            continue
        if not declined:
            continue
        top = re.match(r"^\s*(?:\*\*|[-*]\s*\*\*)?([HM]\d+)\s*,?\s*declined"
                       r"[^:]*:\*?\*?\s*(.+)", line, re.I)
        if top:
            reasons[top.group(1).upper()] = top.group(2).strip()
            continue
        heading = re.match(r"^### ([HM]\d+)\b", line)
        if heading:
            close()
            cur_id, cur_lines = heading.group(1), [line]
        elif cur_id is not None:
            cur_lines.append(line)
    close()
    return reasons


# ---------------------------------------------------------------- processes

def run_shell(command, cwd, input_text=None, timeout=None):
    """Runs a shell command; returns (exit code, stdout, stderr).

    The command gets its own process group so a timeout also stops whatever
    it started, which would otherwise keep the output pipes open. Raises
    subprocess.TimeoutExpired.
    """
    proc = subprocess.Popen(
        command, shell=True, cwd=cwd,
        stdin=(subprocess.PIPE if input_text is not None
               else subprocess.DEVNULL),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace", start_new_session=True)
    try:
        out, err = proc.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise
    return proc.returncode, out, err


def write_atomic(path, text):
    """Writes `text` so readers see the old file or the whole new one."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def main():
    try:
        print("repository: %s" % root())
        print("kit: %s" % KIT_DIR)
        print("prompts and lenses from: %s" % home_dir())
        print("state: %s" % state_dir())
        for key in DEFAULTS:
            value = config(key)
            if key == "forbidMessage" and value == DEFAULT_FORBID_MESSAGE:
                value = "(default)"
            print("%s = %s" % (key, value))
        for key in ("lintCmd", "tidyCmd"):
            for value in config_all(key):
                print("%s = %s" % (key, value))
        print("base ref: %s" % resolve_base())
        print("lenses: %s" % ", ".join(lenses_for(
            changed_files(merge_base(resolve_base()), "HEAD"))))
    except KitError as exc:
        print("kit: %s" % exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
