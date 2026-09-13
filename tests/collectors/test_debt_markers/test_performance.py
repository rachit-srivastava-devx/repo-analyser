"""Proves the O(files-with-matches) blame-batching design blame_age.py's
docstring claims, not just "didn't crash": a repo with many files and many
markers per file must cost one `git blame` subprocess per matched *file*,
not one per matched *line* -- the difference between ~tens of subprocess
calls and thousands on a repo this size.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from repo_analyser.collectors.debt_markers import blame_age
from repo_analyser.collectors.debt_markers.analyze import analyze_repo

from ._debt_markers_helpers import commit_all, init_repo, write

FILE_COUNT = 30
MARKERS_PER_FILE = 25


def _make_marker_file(index: int) -> str:
    lines = [f"# TODO({index}-{i}): backlog item\n" for i in range(MARKERS_PER_FILE)]
    return "".join(lines)


def test_blame_is_called_once_per_file_not_once_per_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(FILE_COUNT):
        write(repo, f"module_{i}.py", _make_marker_file(i))
    commit_all(repo, "many markers across many files")

    call_count = 0
    real_line_author_times = blame_age.line_author_times

    def counting_line_author_times(repo_arg: Path, rel_path: str) -> dict[int, int]:
        nonlocal call_count
        call_count += 1
        return real_line_author_times(repo_arg, rel_path)

    monkeypatch.setattr(
        "repo_analyser.collectors.debt_markers.aggregate.line_author_times",
        counting_line_author_times,
    )

    started = time.monotonic()
    result = analyze_repo(repo)
    elapsed = time.monotonic() - started

    assert result.total_marker_count == FILE_COUNT * MARKERS_PER_FILE
    assert call_count == FILE_COUNT, (
        f"expected one git-blame call per file with a match ({FILE_COUNT}), got {call_count} -- "
        "this almost certainly means blame is being invoked per-marker again, not per-file"
    )
    # Generous bound for a slow CI runner -- the point of this test is the
    # call-count assertion above; this is a coarse sanity check that
    # nothing pathological (e.g. an accidental O(n^2) rescan) crept in.
    assert elapsed < 30.0
