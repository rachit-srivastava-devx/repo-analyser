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
   ubiquitous in C-family/Java block comments). This is what actually
   prevents matching a marker word sitting inside a plain string literal or
   log message (`print("TODO: send email")` is business logic, not a
   tracked debt ticket) -- requiring the marker to originate from something
   that reads as a comment line is the one heuristic doing both jobs, so
   there is no separate string-literal detector to get wrong.

Known, stated limitation: free-form text inside a block comment that
doesn't repeat a leading `*` per line (unusual, but not impossible) is
missed. That is the accepted cost of not writing a real comment grammar.
"""
from __future__ import annotations

import re

MARKER_TYPES = ("TODO", "FIXME", "HACK", "XXX", "BUG")

_COMMENT_PREFIX_RE = re.compile(r"^\s*(?:#|//|/\*+|--|<!--|\*)")
_MARKER_RE = re.compile(r"\b(?:" + "|".join(MARKER_TYPES) + r")\b")


def find_markers_in_text(text: str) -> list[tuple[int, str]]:
    """(1-indexed line number, marker type) for every marker on a
    comment-anchored line. Multiple markers on one line each count
    independently -- a line with two tokens (same type or different)
    yields two entries, one per token, not one entry for the line."""
    matches: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not _COMMENT_PREFIX_RE.match(line):
            continue
        matches.extend((lineno, m.group(0)) for m in _MARKER_RE.finditer(line))
    return matches
