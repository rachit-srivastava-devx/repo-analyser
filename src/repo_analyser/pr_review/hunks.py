"""Parses `git diff --unified=0` output into per-path added-line ranges,
by splitting one combined diff stream on its `diff --git` file boundaries
and reading each file's `@@ ... @@` hunk headers. See `diff.py`'s module
docstring for why one combined stream, not one per changed file.
"""
from __future__ import annotations

import re

# `@@ -a[,b] +c[,d] @@[ optional trailing function-context text]`. b/d are
# omitted by git when the count is exactly 1 (verified empirically: a
# single-line hunk renders as `@@ -3 +3 @@`, not `@@ -3,1 +3,1 @@`).
_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _parse_added_ranges(text: str) -> dict[str, list[tuple[int, int]]]:
    """Splits one combined `git diff --unified=0` stream on `diff --git`
    file boundaries and pulls each file's added-line ranges out of its
    `@@ ... @@` hunk headers.

    A binary file has no `@@` headers at all (git prints "Binary files ...
    differ" instead) and a pure rename with zero content change has no
    `+++`/`@@` lines either (just `similarity index 100%` / `rename
    from`/`rename to`) -- both correctly fall out of this as an empty range
    list, never a crash, since the per-file dict entry is only populated
    from lines that are actually present.
    """
    ranges_by_path: dict[str, list[tuple[int, int]]] = {}
    current_path: str | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current_path = None  # resolved below, from +++ or "rename to"
        elif line.startswith("+++ "):
            rest = line[len("+++ "):]
            current_path = None if rest == "/dev/null" else rest[len("b/"):]
            if current_path is not None:
                ranges_by_path.setdefault(current_path, [])
        elif line.startswith("rename to "):
            current_path = line[len("rename to "):]
            ranges_by_path.setdefault(current_path, [])
        elif current_path is not None and line.startswith("@@ "):
            m = _HUNK_HEADER_RE.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                if count > 0:
                    ranges_by_path[current_path].append((start, start + count - 1))
    return ranges_by_path
