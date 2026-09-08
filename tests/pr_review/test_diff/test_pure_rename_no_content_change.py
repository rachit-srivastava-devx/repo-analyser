"""Tests for pr_review.diff.get_changed_files on a pure rename (no content
change)."""
from __future__ import annotations

from pathlib import Path

from _pr_review_helpers import _ctx
from conftest import _git

from repo_analyser.pr_review.diff import get_changed_files


class TestPureRenameNoContentChange:
    def test_reports_zero_additions_deletions_and_status_r(self, tmp_path: Path) -> None:
        repo = tmp_path / "rename_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "old_name.txt").write_text("line1\nline2\nline3\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add file")
        merge_base = _git(repo, "rev-parse", "HEAD").strip()

        _git(repo, "mv", "old_name.txt", "new_name.txt")
        _git(repo, "commit", "-q", "-m", "pure rename")
        head = _git(repo, "rev-parse", "HEAD").strip()

        changed = get_changed_files(repo, _ctx(merge_base, head))
        assert len(changed) == 1
        cf = changed[0]
        assert cf.status == "R"
        assert cf.old_path == "old_name.txt"
        assert cf.path == "new_name.txt"
        # a pure rename must NOT inflate PR-size numbers -- --find-renames
        # exists precisely so this doesn't show as N deleted + N added.
        assert cf.additions == 0
        assert cf.deletions == 0
        assert cf.added_line_ranges == []
