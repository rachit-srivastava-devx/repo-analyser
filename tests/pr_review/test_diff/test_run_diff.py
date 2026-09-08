"""Tests for pr_review.diff.run_diff."""
from __future__ import annotations

from pathlib import Path

from _pr_review_helpers import _ctx
from conftest import DivergedRepo, _git

from repo_analyser.core.util import read_json
from repo_analyser.pr_review.context import resolve_pr_context
from repo_analyser.pr_review.diff import run_diff


class TestRunDiff:
    def test_writes_json_matching_get_changed_files(self, diverged_repo: DivergedRepo, tmp_path: Path) -> None:
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=diverged_repo.head_sha)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_diff(diverged_repo.repo, ctx, out_dir)
        assert out_path == out_dir / "pr_review_diff.json"
        data = read_json(out_path)
        assert len(data) == 1
        assert data[0]["path"] == "feature.txt"
        assert data[0]["status"] == "A"

    def test_zero_changed_files_writes_empty_list(self, git_repo: Path, tmp_path: Path) -> None:
        head_sha = _git(git_repo, "rev-parse", "HEAD").strip()
        ctx = _ctx(head_sha, head_sha)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_diff(git_repo, ctx, out_dir)
        assert read_json(out_path) == []
