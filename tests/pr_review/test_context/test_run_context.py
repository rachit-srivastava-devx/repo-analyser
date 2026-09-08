"""Tests for pr_review.context.run_context."""
from __future__ import annotations

from pathlib import Path

from conftest import DivergedRepo

from repo_analyser.core.util import read_json
from repo_analyser.pr_review.context import run_context


class TestRunContext:
    def test_writes_json_matching_the_returned_context(
        self, diverged_repo: DivergedRepo, tmp_path: Path,
    ) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_context(
            diverged_repo.repo, out_dir, base=diverged_repo.base_sha, head=diverged_repo.head_sha,
        )
        assert out_path == out_dir / "pr_review_context.json"
        data = read_json(out_path)
        assert data["repo"] == diverged_repo.repo.name
        assert data["merge_base_sha"] == diverged_repo.fork_sha
        assert data["commits_in_range"] == 2
        assert data["resolved_via"] == "explicit"
        assert data["warning"] is None
