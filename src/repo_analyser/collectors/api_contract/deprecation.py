"""Signal 4: deprecation-marker + sunset-date convention scanning. Regex,
line-window based -- works uniformly across OpenAPI YAML/JSON, GraphQL SDL,
and protobuf text without needing a full recursive dict/AST walk, and
degrades gracefully on a malformed spec file (a YAML file that fails to
parse as OpenAPI can still be scanned as plain text for the marker, since
the marker/sunset convention is a textual one, not a structural one this
collector depends on discovery.py's parse succeeding for).

"Deprecated but no sunset signal found nearby" is the interesting finding
this checklist item cares about (docs/checklist-by-repo-type/single-
repo.md's "Deprecation policy enforcement" row) -- both counts are always
reported, never silently dropped to zero.
"""
from __future__ import annotations

from pathlib import Path

from .patterns import DEPRECATED_MARKER_RE, SUNSET_SIGNAL_RE, SUNSET_WINDOW_LINES
from .text_io import read_text_safe


def _has_sunset_nearby(lines: list[str], line_idx: int, extra: str, other_marker_lines: set[int]) -> bool:
    """Window search, clipped so it never crosses into a *different*
    marker's own line -- otherwise two deprecated fields within
    SUNSET_WINDOW_LINES of each other (a common, legitimate spec shape:
    several deprecated fields grouped together) would let one field's real
    sunset date get misattributed to its neighbor."""
    if SUNSET_SIGNAL_RE.search(extra):
        return True
    lo = max(0, line_idx - SUNSET_WINDOW_LINES)
    hi = min(len(lines), line_idx + SUNSET_WINDOW_LINES + 1)
    below = [ln for ln in other_marker_lines if ln < line_idx]
    above = [ln for ln in other_marker_lines if ln > line_idx]
    if below:
        lo = max(lo, max(below) + 1)
    if above:
        hi = min(hi, min(above))
    window = "\n".join(lines[lo:hi])
    return bool(SUNSET_SIGNAL_RE.search(window))


def count_deprecations(path: Path, kind: str) -> tuple[int, int]:
    """Returns (with_sunset, without_sunset) for one spec file. kind is one
    of "openapi"/"graphql"/"protobuf" -- selects which marker regex to use.
    A file that can't be read as text (see text_io.read_text_safe)
    contributes (0, 0): its unreadability is already reported separately as
    a parse/read error by discovery.py, not double-counted here."""
    text, err = read_text_safe(path)
    if err or text is None:
        return 0, 0
    pattern = DEPRECATED_MARKER_RE[kind]
    lines = text.splitlines()
    matches = list(pattern.finditer(text))
    match_lines = [text.count("\n", 0, m.start()) for m in matches]
    with_sunset = without_sunset = 0
    for i, m in enumerate(matches):
        line_idx = match_lines[i]
        extra = m.group(1) if kind == "graphql" and m.lastindex else ""
        other_lines = {ln for j, ln in enumerate(match_lines) if j != i}
        if _has_sunset_nearby(lines, line_idx, extra or "", other_lines):
            with_sunset += 1
        else:
            without_sunset += 1
    return with_sunset, without_sunset
