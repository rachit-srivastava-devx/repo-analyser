from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.debt_markers.discovery import iter_tracked_files, read_text_or_none

from ._debt_markers_helpers import commit_all, git, init_repo, write, write_bytes


def test_iter_tracked_files_on_empty_repo_is_empty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    assert iter_tracked_files(repo) == []


def test_iter_tracked_files_excludes_untracked_and_gitignored(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "tracked.py", "# TODO: tracked\n")
    commit_all(repo, "init")
    write(repo, "untracked.py", "# TODO: never added\n")
    write(repo, ".gitignore", "ignored.py\n")
    write(repo, "ignored.py", "# TODO: gitignored\n")

    tracked = {p.name for p in iter_tracked_files(repo)}
    assert tracked == {"tracked.py"}


def test_iter_tracked_files_includes_staged_but_uncommitted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "staged.py", "# TODO: staged only\n")
    git(repo, "add", "staged.py")

    tracked = {p.name for p in iter_tracked_files(repo)}
    assert tracked == {"staged.py"}


def test_read_text_or_none_reads_real_utf8_text(tmp_path: Path) -> None:
    p = tmp_path / "a.py"
    p.write_text("# TODO: hello\n", encoding="utf-8")
    assert read_text_or_none(p) == "# TODO: hello\n"


def test_read_text_or_none_returns_none_for_null_byte_binary_content(tmp_path: Path) -> None:
    p = write_bytes(tmp_path, "blob.bin", b"\x00\x01\x02TODO\x00binary")
    assert read_text_or_none(p) is None


def test_read_text_or_none_returns_none_for_non_utf8_bytes(tmp_path: Path) -> None:
    p = write_bytes(tmp_path, "latin1.py", "# TODO: caf\xe9\n".encode("latin-1"))
    assert read_text_or_none(p) is None


def test_read_text_or_none_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert read_text_or_none(tmp_path / "does_not_exist.py") is None
