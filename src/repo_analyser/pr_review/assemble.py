"""Combines each parsed diff component (name-status entries, numstat
counts, added-line ranges, generated-file flags) into the final
`ChangedFile` list that `diff.py`'s `get_changed_files` returns.
"""
from __future__ import annotations

from pathlib import Path

from ..core.lang import EXCLUDE_DIR_PARTS
from .diff_models import ChangedFile
from .flags import _LOCKFILE_NAMES


def _assemble_changed_files(
    entries: list[tuple[str, str, str | None]],
    stats: dict[str, tuple[int, int]],
    ranges_by_path: dict[str, list[tuple[int, int]]],
    gen_flags: dict[str, bool],
) -> list[ChangedFile]:
    changed_files = []
    for status, path, old_path in entries:
        additions, deletions = stats.get(path, (0, 0))
        parts = Path(path).parts
        changed_files.append(ChangedFile(
            path=path,
            status=status,
            old_path=old_path,
            additions=additions,
            deletions=deletions,
            added_line_ranges=ranges_by_path.get(path, []),
            is_lockfile=Path(path).name in _LOCKFILE_NAMES,
            is_generated=gen_flags.get(path, False),
            is_excluded=any(part in EXCLUDE_DIR_PARTS for part in parts),
        ))
    return changed_files
