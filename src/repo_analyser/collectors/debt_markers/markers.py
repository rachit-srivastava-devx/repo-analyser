"""Debt-marker scanning: which lines of a file's text carry a `TODO`,
`FIXME`, `HACK`, `XXX`, or `BUG` marker.

Two deliberate, combined heuristics -- not a per-language comment parser
(out of scope per the brief):

1. **Word-boundary matching** (`\\bTODO\\b`, not a bare substring search) --
   defeats the "TODOLIST"/"DEBUGGING" class of false positive, where the
   marker text is really just part of an unrelated identifier or word.
2. **Comment-prefix anchoring** -- a marker is only counted on a line whose
   *stripped* text starts with one of the common single-line/block comment
   openers named in the brief (`#`, `//`, `/*`, `--`, `<!--`), plus `*` for
   a block-comment continuation line (`/* ... \\n * TODO: ... \\n */`,
   ubiquitous in C-family/Java block comments).

Comment-prefix anchoring alone does *not* fully cover the string-literal
case: a per-line regex has no concept of "am I currently inside an open
multi-line string", so a triple-quoted Python string whose contents happen
to look like a comment (`# TODO: ...` as literal string *data*) would
otherwise be flagged. To close that specific, real gap, `.py` files get one
extra, narrow pass (`_lines_inside_python_triple_quoted_string`): lines that
fall between an open and close `\"\"\"`/`'''` are excluded from matching
before the comment-prefix check ever runs.

**What is and isn't covered, stated plainly (no blanket "solved" claim):**
- Covered: Python triple-quoted strings (`\"\"\"`/`'''`), line-granularity,
  for files whose name ends in `.py`.
- Not covered: multi-line string/heredoc literals in any other language
  (JS/TS template literals, Go/Rust raw strings, shell heredocs, ...);
  C-style `/* ... */` block comments spanning many lines (a separate,
  harder problem than the string case -- still relies on the `*`
  continuation-prefix heuristic above, which is a real but incomplete
  cost); a triple-quote that is itself escaped or embedded inside a
  single-quoted string on the same line; and any single-line string
  literal, which was never this module's job to detect in the first place
  -- the comment-prefix anchor is still the only thing preventing a match
  there, and it works precisely because a single-line string like
  `print("TODO: send email")` does not start with a recognized comment
  prefix. There is no general-purpose string-literal detector here, only
  the narrow Python triple-quote tracker described above.
"""
from __future__ import annotations

import re

MARKER_TYPES = ("TODO", "FIXME", "HACK", "XXX", "BUG")

_COMMENT_PREFIX_RE = re.compile(r"^\s*(?:#|//|/\*+|--|<!--|\*)")
_MARKER_RE = re.compile(r"\b(?:" + "|".join(MARKER_TYPES) + r")\b")
_TRIPLE_QUOTE_RE = re.compile(r"\"\"\"|'''")


def _lines_inside_python_triple_quoted_string(lines: list[str]) -> list[bool]:
    """For each physical line (same indexing as `lines`), True if that
    line's content sits inside an already-open triple-quoted string
    literal at the moment the line *starts*.

    Heuristic, not a tokenizer: counts raw `\"\"\"`/`'''` occurrences per
    line (combined, in the order they appear) and toggles an "inside
    string" flag once per occurrence. It does not understand backslash
    escaping of a quote character, a string prefix letter (r/f/b) in front
    of the opening triple-quote (still just three quote characters to this
    scan either way), or a triple-quote delimiter that is itself embedded
    inside a *different* single-quoted string on the same line. Good
    enough to close the real, reported false-positive (a `# TODO: ...`
    -shaped line sitting inside a `\"\"\"`-delimited banner string) without
    writing a real Python tokenizer, per module docstring.
    """
    inside = False
    flags: list[bool] = []
    for line in lines:
        flags.append(inside)
        if len(_TRIPLE_QUOTE_RE.findall(line)) % 2 == 1:
            inside = not inside
    return flags


def find_markers_in_text(text: str, filename: str | None = None) -> list[tuple[int, str]]:
    """(1-indexed line number, marker type) for every marker on a
    comment-anchored line. Multiple markers on one line each count
    independently -- a line with two tokens (same type or different)
    yields two entries, one per token, not one entry for the line.

    `filename` is optional and used only to decide whether the Python
    triple-quoted-string suppression applies (`.py` files); omit it (or
    pass a non-`.py` name) to get the plain comment-prefix behavior with
    no string tracking, e.g. for a language this module doesn't special-case.
    """
    lines = text.splitlines()
    in_string = (
        _lines_inside_python_triple_quoted_string(lines)
        if filename is not None and filename.endswith(".py")
        else [False] * len(lines)
    )
    matches: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        if in_string[lineno - 1]:
            continue
        if not _COMMENT_PREFIX_RE.match(line):
            continue
        matches.extend((lineno, m.group(0)) for m in _MARKER_RE.finditer(line))
    return matches
