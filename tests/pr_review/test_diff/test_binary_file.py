"""Tests for pr_review.diff.get_changed_files on a binary file."""
from __future__ import annotations

from pathlib import Path

from _pr_review_helpers import _ctx
from conftest import _git

from repo_analyser.pr_review.diff import get_changed_files


class TestBinaryFile:
    def test_binary_file_has_zero_counts_and_no_added_ranges(self, tmp_path: Path) -> None:
        repo = tmp_path / "binary_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "commit", "--allow-empty", "-q", "-m", "empty root")
        merge_base = _git(repo, "rev-parse", "HEAD").strip()

        (repo / "image.bin").write_bytes(bytes([0, 1, 2, 255, 254, 0, 0]))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add binary file")
        head = _git(repo, "rev-parse", "HEAD").strip()

        changed = get_changed_files(repo, _ctx(merge_base, head))
        assert len(changed) == 1
        cf = changed[0]
        assert cf.path == "image.bin"
        assert cf.status == "A"
        assert cf.additions == 0
        assert cf.deletions == 0
        assert cf.added_line_ranges == []
