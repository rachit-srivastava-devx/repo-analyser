from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from repo_analyser.collectors.debt_markers import blame_age
from repo_analyser.collectors.debt_markers.blame_age import line_author_times
from repo_analyser.core.util import RunResult

from ._debt_markers_helpers import commit_all_at, init_repo, write

_DATE_A = "2024-01-10T12:00:00+00:00"
_DATE_B = "2024-06-15T09:30:00+00:00"


def _epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp())


def test_line_author_times_maps_each_line_to_its_introducing_commit(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "f.py", "line1\n# TODO: old one\nline3\n")
    commit_all_at(repo, "first", _DATE_A)
    write(repo, "f.py", "line1\n# TODO: old one\nline3\n# FIXME: newer one\n")
    commit_all_at(repo, "second", _DATE_B)

    mapping = line_author_times(repo, "f.py")

    assert mapping[2] == _epoch(_DATE_A)
    assert mapping[4] == _epoch(_DATE_B)


def test_line_author_times_for_uncommitted_change_is_roughly_now(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "f.py", "line1\n")
    commit_all_at(repo, "first", _DATE_A)
    write(repo, "f.py", "line1\n# TODO: not committed yet\n")

    mapping = line_author_times(repo, "f.py")

    now = datetime.now(timezone.utc).timestamp()
    assert abs(now - mapping[2]) < 60


def test_line_author_times_empty_for_nonexistent_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "f.py", "line1\n")
    commit_all_at(repo, "first", _DATE_A)

    assert line_author_times(repo, "does_not_exist.py") == {}


def test_line_author_times_empty_when_repo_has_no_commits(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "f.py", "line1\n")
    # f.py is written but never committed or staged -- blame has no history
    # to walk at all.
    assert line_author_times(repo, "f.py") == {}


def test_line_author_times_tolerates_a_malformed_header_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive parsing: a header line whose 3rd token isn't a valid
    integer (should never happen with real git output, but the parser
    must not crash on it) is skipped rather than raising, and a genuine
    line right after it still parses correctly."""
    fake_stdout = (
        "abc1234 1 not_a_number 1\n"
        "author Test\n"
        "author-time 1700000000\n"
        "\tgarbage header line, ignored\n"
        "def5678 2 2 1\n"
        "author Test\n"
        "author-time 1710000000\n"
        "\treal line\n"
    )

    def fake_run(*_args: object, **_kwargs: object) -> RunResult:
        return RunResult(cmd=["git", "blame"], returncode=0, stdout=fake_stdout, stderr="")

    monkeypatch.setattr(blame_age, "run", fake_run)

    mapping = line_author_times(tmp_path, "whatever.py")

    assert mapping == {2: 1710000000}


def test_line_author_times_tolerates_a_malformed_author_time_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_stdout = (
        "abc1234 1 1 1\n"
        "author Test\n"
        "author-time not_a_number\n"
        "\tline with unparseable timestamp\n"
        "def5678 2 2 1\n"
        "author Test\n"
        "author-time 1710000000\n"
        "\tline with a real timestamp\n"
    )

    def fake_run(*_args: object, **_kwargs: object) -> RunResult:
        return RunResult(cmd=["git", "blame"], returncode=0, stdout=fake_stdout, stderr="")

    monkeypatch.setattr(blame_age, "run", fake_run)

    mapping = line_author_times(tmp_path, "whatever.py")

    assert mapping == {2: 1710000000}
