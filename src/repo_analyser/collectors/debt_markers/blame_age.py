"""Age of a specific line, via `git blame`.

**Complexity, stated plainly**: this calls `git blame --line-porcelain`
*once per file that has at least one marker match*, not once per matched
line/marker. A file with 40 TODOs costs one subprocess call, not 40 --
that's O(F) git invocations (F = files with >=1 match), each itself
O(lines in that file), rather than the naive O(M) (M = total marker count)
per-line design a first draft might reach for. For a huge repo with
thousands of markers concentrated in relatively few files this is the
difference between a handful of subprocess calls and thousands.

Parsing follows escape.py's `_blame_map` precedent (same porcelain header
shape, same defensive full-hex-sha + non-metadata-line check) but reads
`author-time` instead of the introducing sha, since the brief only needs
each line's age, and `--line-porcelain` (unlike plain `--porcelain`)
repeats full metadata after every single header line -- no cross-line
"which commit does this short header refer to" state to track.

A line git blame attributes to the all-zero "Not Committed Yet" pseudo-commit
(an uncommitted/staged working-tree change) still gets a real author-time
(effectively "now"), so it naturally reports as a ~0-day-old marker rather
than crashing or requiring special-casing -- an honest reading of "how old
is this line", not a distinct code path.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...core.util import run

_HEADER_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def line_author_times(repo: Path, rel_path: str) -> dict[int, int]:
    """final line number (1-indexed, current working-tree content) -> the
    introducing/last-touching commit's author-time (unix epoch seconds).
    Empty dict on any blame failure (deleted path, git error) -- callers
    treat a missing entry as "age unknown", not a crash."""
    res = run(["git", "blame", "--line-porcelain", "--", rel_path], cwd=repo, check=False)
    if res.returncode != 0:
        return {}
    mapping: dict[int, int] = {}
    current_line: int | None = None
    for raw_line in res.stdout.splitlines():
        parts = raw_line.split()
        if (parts and _HEADER_SHA_RE.fullmatch(parts[0]) and len(parts) >= 3
                and not raw_line.startswith(("author ", "committer ", "summary "))):
            try:
                current_line = int(parts[2])
            except ValueError:
                current_line = None
            continue
        if raw_line.startswith("author-time ") and current_line is not None:
            try:
                mapping[current_line] = int(raw_line.split(maxsplit=1)[1])
            except (ValueError, IndexError):
                pass
    return mapping
