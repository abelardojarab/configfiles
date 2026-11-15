#!/usr/bin/env python3
"""Code-quality sweep: prints suspected nits on the lines a change adds.

Usage:
  cq_sweep.py [--staged | --commit REV | --range A..B] [--strict]

  --staged      the index against HEAD (what the pre-commit hook checks)
  --commit REV  one commit (default: --commit HEAD)
  --range A..B  the combined diff of a range
  --strict      exit 1 when anything is printed

Each check prints a named section of `file: text` lines, only when it has
findings, and `clean` when none has. Files are read as they are at the
checked revision (the index for --staged), never from the work tree. The
column limit is reviewkit.maxCols and the size limit is reviewkit.maxLines;
0 disables either.

Exit codes:
  0  clean, or findings without --strict
  1  findings with --strict
  2  the revision or the repository could not be read
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

MAX_PER_SECTION = 20
LINE_NUMBER_REF = re.compile(r"\b[Ll]ines? \d+|:\d+-\d+\b|;l=\d")
BRACELESS_BODY = re.compile(
    r"^\s*(?:if|for)\s*\(.*\)\s*(?:continue|return|break)\b[^{]*;")
LOCAL_CONSTEXPR_ARRAY = re.compile(
    r"^\s{2,}(?:static\s+)?constexpr\s[^=]*\[\]")
KEEP_IN_SYNC = re.compile(r"keep\b.*\bin sync|must match|\bmirrors?\s", re.I)
SINGLE_LETTER = re.compile(
    r"\bas [a-z]\b|\bfor\s*\(.*[^\w:][a-hj-z]\s*:[^:]|\bfor [a-hj-z] in "
    r"|\bauto\s*&?\s*[a-hj-z]\s*=")
INLINE_SCALAR = re.compile(
    r"^inline\s+(?:double|float|bool|int|unsigned|long|size_t"
    r"|u?int(?:8|16|32|64)_t)\s")
DUPLICATE_LOOKUP = re.compile(
    r"std::pair\(([A-Za-z0-9_]+\([^)]+\))\.[A-Za-z0-9_]+\(\),\s*\1\.")
FIXED_WIDTH = re.compile(r"\bu?int(?:8|16|32|64)_t\b")
TUPLE_USE = re.compile(r"\bstd::(?:tuple|make_tuple|tie|get)\b")
UTILITY_USE = re.compile(r"\bstd::(?:pair|make_pair|move|forward|exchange)\b")
# What each standard header provides that a file would name; an include with
# none of these in the file is probably left over.
HEADER_SYMBOLS = {
    "tuple": r"tuple|make_tuple|tie|get|apply|tuple_size|tuple_element"
             r"|forward_as_tuple|ignore",
    "array": r"array|to_array|get",
    "vector": r"vector",
    "map": r"map|multimap",
    "set": r"set|multiset",
    "optional": r"optional|make_optional|nullopt|nullopt_t"
                r"|bad_optional_access",
    "utility": r"pair|make_pair|move|forward|exchange|swap|get|declval"
               r"|as_const|in_place|index_sequence|make_index_sequence"
               r"|integer_sequence|piecewise_construct|move_if_noexcept",
}


def _header_included(text, header):
    return re.search(r"^\s*#\s*include\s*<" + header + r">", text,
                     re.M) is not None


def sweep(diff, read_file, max_lines, max_cols, size_exempt=False):
    """Runs every check. `read_file(path)` returns a file's text at the
    checked revision, or None. Returns [(section title, [finding])]."""
    found = []

    def section(title, items):
        if items:
            found.append((title, items))

    added = kit.added_lines(diff)
    size = kit.changed_line_count(diff)
    if max_lines > 0 and size > max_lines and not size_exempt:
        section("Size over reviewkit.maxLines (split it by problem)",
                ["%d changed lines (limit %d)" % (size, max_lines)])

    texts = {}

    def text_of(path):
        if path not in texts:
            texts[path] = read_file(path)
        return texts[path]

    line_refs, issues, braceless, constexpr_arrays = [], [], [], []
    sync, long_lines, docstrings, single, inline_scalar = [], [], [], [], []
    lookups, make_optional, protos, includes = [], [], [], []
    map_reads, map_invariants = [], []
    for path in sorted(added):
        lines = added[path]
        markdown = kit.is_markdown(path)
        c_family = kit.is_c_family(path)
        python = path.endswith((".py", ".pyi"))
        has_marker = kit.comment_marker(path) is not None
        for line_no, text in sorted(lines.items()):
            where = "%s:%d: " % (path, line_no)
            comment = text.strip() if markdown else kit.comment_text(path,
                                                                     text)
            code = kit.split_comment(path, text)[0]
            if comment and LINE_NUMBER_REF.search(comment):
                line_refs.append(where + text.strip())
            if not markdown and comment and "TODO(" not in comment:
                refs = kit.issue_refs(comment)
                if refs:
                    issues.append(where + text.strip())
            if not markdown and comment and KEEP_IN_SYNC.search(comment):
                sync.append(where + text.strip())
            if c_family and BRACELESS_BODY.search(code):
                braceless.append(where + text.strip())
            if c_family and LOCAL_CONSTEXPR_ARRAY.search(code):
                constexpr_arrays.append(where + text.strip())
            if (max_cols > 0 and has_marker and len(text) > max_cols
                    and "://" not in text and "#include" not in text):
                long_lines.append(where + "%d columns" % len(text))
            if (python and max_cols > 0
                    and re.match(r'^\s*[rRbBuU]?"""', text)
                    and len(text) > max_cols):
                docstrings.append(where + text.strip())
            if (python or c_family) and SINGLE_LETTER.search(code):
                single.append(where + text.strip())
            if kit.is_header(path) and INLINE_SCALAR.search(text):
                inline_scalar.append(where + text.strip())
            if c_family and DUPLICATE_LOOKUP.search(code):
                lookups.append(where + text.strip())
            if c_family and "std::make_optional(" in code:
                make_optional.append(where + text.strip())
            if path.endswith(".proto") and re.match(r"^message\s", text):
                full = text_of(path) or ""
                file_lines = full.splitlines()
                prev = (file_lines[line_no - 2]
                        if 1 < line_no <= len(file_lines) + 1 else "")
                if "Next ID" not in prev:
                    protos.append(where + text.strip())

        if c_family:
            full = text_of(path)
            if full is not None:
                codes = [kit.split_comment(path, t)[0]
                         for t in lines.values()]
                if (kit.is_header(path)
                        and any(FIXED_WIDTH.search(c) for c in codes)
                        and not _header_included(full, "cstdint")):
                    includes.append("%s: fixed-width ints added without "
                                    "#include <cstdint>" % path)
                if (any(TUPLE_USE.search(c) for c in codes)
                        and not _header_included(full, "tuple")):
                    includes.append("%s: std::tuple added without "
                                    "#include <tuple>" % path)
                if (any(UTILITY_USE.search(c) for c in codes)
                        and not _header_included(full, "utility")):
                    includes.append("%s: std::pair or std::move added "
                                    "without #include <utility>" % path)
                code_text = "\n".join(kit.split_comment(path, t)[0]
                                      for t in full.splitlines())
                for header, symbols in sorted(HEADER_SYMBOLS.items()):
                    if (_header_included(full, header)
                            and not re.search(r"\bstd::(?:" + symbols
                                              + r")\b", code_text)):
                        includes.append("%s: <%s> is included but nothing "
                                        "from it is used" % (path, header))
                if kit.is_cpp(path):
                    reads, invariants = kit.map_index_problems(
                        path, full, set(lines))
                    map_reads += reads
                    map_invariants += invariants

    section("Line numbers in added comments or docs (name the symbol)",
            line_refs)
    section("Issue references in comments outside a TODO( (the message "
            "carries them)", issues)
    section("One-line if/for bodies without braces", braceless)
    section("Function-local constexpr arrays (move to namespace scope)",
            constexpr_arrays)
    section("'Keep in sync' comments (share the code, or add a check that "
            "fails when one side changes alone)", sync)
    section("Added lines over reviewkit.maxCols (%d)" % max_cols, long_lines)
    section("Python docstring summary lines over reviewkit.maxCols",
            docstrings)
    section("Single-letter names", single)
    section("Includes", includes)
    section("Inline scalar functions in headers (prefer constexpr)",
            inline_scalar)
    section("Lookup call repeated inside EXPECT_EQ(std::pair(...)) (bind it "
            "once)", lookups)
    section("std::make_optional( (std::optional(value) reads the same next "
            "to std::nullopt)", make_optional)
    section("New proto messages without a // Next ID comment above them",
            protos)
    section("Reads through a map's operator[], which inserts on a miss (use "
            "find(), or at() where the key always exists)", map_reads)
    section("Map lookups whose key does not change inside the loop (hoist "
            "them, unless the loop inserts into the map)", map_invariants)
    return found


def render(found):
    """The sweep's printed form."""
    if not found:
        return "clean"
    out = []
    for title, items in found:
        out.append("== " + title)
        out.extend(items[:MAX_PER_SECTION])
        if len(items) > MAX_PER_SECTION:
            out.append("... %d more" % (len(items) - MAX_PER_SECTION))
    return "\n".join(out)


def sweep_commit(rev, max_lines, max_cols):
    """sweep() over one commit, its files read at that commit."""
    exempt = bool(kit.MOVE_ONLY.search(kit.subject(kit.message(rev))))
    return sweep(kit.commit_diff(rev), lambda p: kit.file_text(rev, p),
                 max_lines, max_cols, size_exempt=exempt)


def main(argv):
    parser = argparse.ArgumentParser(
        description="Code-quality sweep over the lines a change adds.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--commit", metavar="REV")
    mode.add_argument("--range", metavar="A..B", dest="rev_range")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        max_lines = kit.config_int("maxLines")
        max_cols = kit.config_int("maxCols")
        if args.staged:
            found = sweep(kit.staged_diff(), lambda p: kit.file_text(None, p),
                          max_lines, max_cols)
        elif args.rev_range:
            old, sep, new = args.rev_range.partition("..")
            if not sep or not old or not new or new.startswith("."):
                parser.error("--range takes A..B")
            new_commit = kit.rev_parse(new)
            found = sweep(kit.range_diff(kit.rev_parse(old), new_commit),
                          lambda p: kit.file_text(new_commit, p),
                          max_lines, max_cols)
        else:
            rev = kit.rev_parse(args.commit or "HEAD")
            found = sweep_commit(rev, max_lines, max_cols)
    except kit.KitError as exc:
        print("cq_sweep: %s" % exc, file=sys.stderr)
        return 2
    print(render(found))
    return 1 if found and args.strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
