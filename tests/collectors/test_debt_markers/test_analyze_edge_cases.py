from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.debt_markers.analyze import analyze_repo

from ._debt_markers_helpers import commit_all, commit_all_at, git, init_repo, write, write_bytes


def test_nonexistent_path_reports_skip_reason(tmp_path: Path) -> None:
    result = analyze_repo(tmp_path / "does_not_exist")
    assert result.skip_reason != ""
    assert result.total_marker_count == 0
    assert result.marker_counts_by_type == ""


def test_directory_that_is_not_a_git_repo_reports_skip_reason(tmp_path: Path) -> None:
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    write(plain_dir, "a.py", "# TODO: not in a repo\n")
    result = analyze_repo(plain_dir)
    assert "not a git repository" in result.skip_reason


def test_repo_with_no_commits_and_zero_markers_is_not_skipped(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    result = analyze_repo(repo)
    assert result.skip_reason == ""
    assert result.total_marker_count == 0
    assert result.average_age_days == 0.0
    assert result.oldest_marker_age_days == 0
    assert result.stale_marker_count == 0


def test_repo_with_commits_but_zero_markers_is_a_real_result_not_a_skip(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "clean.py", "def add(a, b):\n    return a + b\n")
    commit_all(repo, "clean code, no debt markers")
    result = analyze_repo(repo)
    assert result.skip_reason == ""
    assert result.total_marker_count == 0


def test_repo_with_no_commits_but_a_staged_marker_does_not_crash(tmp_path: Path) -> None:
    """A repo with no commits at all: git blame has no HEAD to walk, so the
    marker's age comes back unknown (excluded from the average/oldest), but
    the marker itself is still counted -- not a crash, not silently
    dropped."""
    repo = init_repo(tmp_path / "r")
    write(repo, "staged.py", "# TODO: staged, never committed\n")
    git(repo, "add", "staged.py")

    result = analyze_repo(repo)

    assert result.skip_reason == ""
    assert result.total_marker_count == 1
    assert result.average_age_days == 0.0
    assert result.oldest_marker_age_days == 0


def test_binary_file_with_marker_like_bytes_does_not_crash_or_match(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write_bytes(repo, "blob.bin", b"# TODO: \x00\x01\x02 embedded in binary junk")
    commit_all(repo, "add binary")

    result = analyze_repo(repo)

    assert result.skip_reason == ""
    assert result.total_marker_count == 0


def test_non_utf8_file_does_not_crash_the_scan(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write_bytes(repo, "latin1.py", "# TODO: caf\xe9 fix encoding\n".encode("latin-1"))
    write(repo, "clean.py", "# FIXME: this one is fine\n")
    commit_all(repo, "mixed encodings")

    result = analyze_repo(repo)

    assert result.skip_reason == ""
    # latin1.py is skipped entirely (undecodable); clean.py's marker still counts.
    assert result.total_marker_count == 1
    assert result.marker_counts_by_type == "FIXME:1"


def test_marker_line_moved_within_a_later_commit_gets_blames_current_history(tmp_path: Path) -> None:
    """Rename/move-following is explicitly a nice-to-have, not required
    (see blame_age.py's docstring) -- this only asserts the collector
    doesn't crash and still reports *some* age for a marker line that moved
    within the same file across commits, not that the age is the original
    line's true first-introduction date."""
    repo = init_repo(tmp_path / "r")
    write(repo, "f.py", "# TODO: will move\nkeep\n")
    commit_all_at(repo, "first", "2024-01-01T00:00:00+00:00")
    write(repo, "f.py", "keep\n\n\n# TODO: will move\n")
    commit_all_at(repo, "moved", "2024-06-01T00:00:00+00:00")

    result = analyze_repo(repo)

    assert result.skip_reason == ""
    assert result.total_marker_count == 1
