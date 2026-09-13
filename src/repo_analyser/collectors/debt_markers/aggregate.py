"""Scans every tracked file once, batch-blames only the files that had a
marker hit (see blame_age.py's docstring for why that ordering matters at
scale), and rolls the result up into one MarkerAggregate per repo."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .blame_age import line_author_times
from .discovery import iter_tracked_files, read_text_or_none
from .markers import find_markers_in_text

# A TODO/FIXME that has survived this long is, empirically, not getting
# picked up by ordinary sprint/backlog grooming -- roughly double a
# quarterly planning cycle (~90 days), the same "give it one extra full
# cycle before calling it stale" reasoning codebase_modularity/
# module_size.py's thresholds use, just for time-since-introduced rather
# than LOC/file-count. A named, documented default, not tuned per repo.
STALE_MARKER_AGE_DAYS = 180


@dataclass
class MarkerAggregate:
    by_type: Counter[str]
    ages: list[int]
    oldest_age: int | None
    oldest_location: str


def collect(repo: Path, now_epoch: int) -> MarkerAggregate:
    by_type: Counter[str] = Counter()
    ages: list[int] = []
    oldest_age: int | None = None
    oldest_location = ""

    for path in iter_tracked_files(repo):
        text = read_text_or_none(path)
        if text is None:
            continue
        found = find_markers_in_text(text)
        if not found:
            continue
        rel_path = str(path.relative_to(repo))
        timestamps = line_author_times(repo, rel_path)
        for lineno, marker_type in found:
            by_type[marker_type] += 1
            ts = timestamps.get(lineno)
            if ts is None:
                continue
            age = (now_epoch - ts) // 86400
            ages.append(age)
            if oldest_age is None or age > oldest_age:
                oldest_age = age
                oldest_location = f"{rel_path}:{lineno}"

    return MarkerAggregate(by_type, ages, oldest_age, oldest_location)
