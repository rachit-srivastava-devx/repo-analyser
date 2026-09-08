"""The per-file result shape `diff.py`'s `get_changed_files` returns one of,
for every file touched in a PR's `merge_base_sha..head_sha` range.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChangedFile:
    path: str
    status: str  # "A" | "M" | "D" | "R" (whatever single-letter status git's
                 # --name-status reports; --find-renames is passed, --find-
                 # copies is not, so "C" never occurs here)
    old_path: str | None  # non-None only when status == "R"
    additions: int
    deletions: int
    added_line_ranges: list[tuple[int, int]]  # 1-indexed, inclusive [start, end]
    is_lockfile: bool
    is_generated: bool
    is_excluded: bool
