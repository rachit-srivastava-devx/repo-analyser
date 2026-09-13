from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from repo_analyser.collectors.debt_markers.aggregate import STALE_MARKER_AGE_DAYS
from repo_analyser.collectors.debt_markers.analyze import analyze_repo

from ._debt_markers_helpers import commit_all_at, init_repo, write

_NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)


def _days_ago(days: int) -> str:
    epoch = _NOW.timestamp() - days * 86400
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def test_analyze_repo_computes_counts_and_ages_against_a_fixed_now(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "old.py", "# TODO: ancient debt\n")
    commit_all_at(repo, "old", _days_ago(400))
    write(repo, "new.py", "# FIXME: recent debt\n")
    commit_all_at(repo, "new", _days_ago(10))

    result = analyze_repo(repo, now=_NOW)

    assert result.skip_reason == ""
    assert result.total_marker_count == 2
    assert result.marker_counts_by_type == "FIXME:1;TODO:1"
    assert result.oldest_marker_age_days == 400
    assert result.oldest_marker_location == "old.py:1"
    assert result.average_age_days == 205.0
    assert result.stale_marker_count == 1
    assert STALE_MARKER_AGE_DAYS == 180


def test_analyze_repo_marker_older_than_threshold_counts_as_stale(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "a.py", "# HACK: right at the edge\n")
    commit_all_at(repo, "a", _days_ago(STALE_MARKER_AGE_DAYS + 1))

    result = analyze_repo(repo, now=_NOW)

    assert result.stale_marker_count == 1


def test_analyze_repo_marker_at_exactly_threshold_is_not_stale(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "a.py", "# HACK: right at the edge\n")
    commit_all_at(repo, "a", _days_ago(STALE_MARKER_AGE_DAYS))

    result = analyze_repo(repo, now=_NOW)

    assert result.stale_marker_count == 0


def test_analyze_repo_multiple_marker_types_are_all_counted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "a.py", "# TODO: a\n# FIXME: b\n# HACK: c\n# XXX: d\n# BUG: e\n")
    commit_all_at(repo, "all-types", _days_ago(5))

    result = analyze_repo(repo, now=_NOW)

    assert result.total_marker_count == 5
    assert result.marker_counts_by_type == "BUG:1;FIXME:1;HACK:1;TODO:1;XXX:1"
