"""Parses `git diff --numstat -z` output into per-path (additions,
deletions) counts. See `name_status.py`'s module docstring for why `-z`.
"""
from __future__ import annotations

from .name_status import _drop_trailing_empty


def _parse_numstat_z(text: str) -> dict[str, tuple[int, int]]:
    """`git diff --numstat -z` output -> `{path: (additions, deletions)}`,
    keyed by the NEW path for a rename. Binary files report `-`/`-` for
    both counts (no line-based diff exists) -- mapped to 0/0 here, which is
    also correct for downstream PR-size metrics: a binary file has no text
    lines to count."""
    tokens = _drop_trailing_empty(text.split("\0"))
    stats: dict[str, tuple[int, int]] = {}
    i = 0
    while i < len(tokens):
        added_s, deleted_s, rest = tokens[i].split("\t", 2)
        added = 0 if added_s == "-" else int(added_s)
        deleted = 0 if deleted_s == "-" else int(deleted_s)
        if rest == "":
            # rename/copy: the combined-path field is empty; the next two
            # tokens are old_path, new_path.
            new_path = tokens[i + 2]
            stats[new_path] = (added, deleted)
            i += 3
        else:
            stats[rest] = (added, deleted)
            i += 1
    return stats
