"""Tests for pr_review.merge_base._merge_base."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import DivergedRepo, _git

from repo_analyser.core.util import ToolExecutionError
from repo_analyser.pr_review.merge_base import _merge_base
from repo_analyser.pr_review.ref_resolution import _verify_ref


class TestMergeBase:
    def test_diverged_branches_resolve_to_the_fork_point(self, diverged_repo: DivergedRepo) -> None:
        result = _merge_base(diverged_repo.repo, diverged_repo.base_sha, diverged_repo.head_sha)
        assert result == diverged_repo.fork_sha

    def test_base_equals_head_returns_that_same_sha(self, git_repo: Path) -> None:
        head = _verify_ref(git_repo, "HEAD")
        assert _merge_base(git_repo, head, head) == head

    def test_shallow_clone_raises_actionable_error_naming_the_fix(
        self, diverged_repo: DivergedRepo, tmp_path: Path,
    ) -> None:
        """The single most common real-world merge-base failure: a shallow
        checkout (GitHub Actions' checkout@v4 default is fetch-depth: 1)
        never fetched enough history for base and head to share a visible
        common ancestor. Verified empirically before writing context.py
        that this fails with returncode 1 and EMPTY stdout/stderr -- so the
        bare git failure alone would tell a user nothing; the error must
        explicitly name the fix.
        """
        shallow = tmp_path / "shallow"
        shallow.mkdir()
        _git(shallow, "init", "-q", "-b", "main")
        _git(shallow, "remote", "add", "origin", f"file://{diverged_repo.repo}")
        _git(shallow, "fetch", "-q", "--depth=1", "origin", "main")
        _git(shallow, "fetch", "-q", "--depth=1", "origin", "feature")
        shallow_base = _verify_ref(shallow, "origin/main")
        shallow_head = _verify_ref(shallow, "origin/feature")

        with pytest.raises(ToolExecutionError) as exc_info:
            _merge_base(shallow, shallow_base, shallow_head)
        assert "fetch-depth" in str(exc_info.value)

    def test_genuinely_unrelated_histories_names_that_possibility_not_just_shallow(
        self, git_repo: Path,
    ) -> None:
        """A repo that is NOT shallow can still legitimately have two
        commits with no common ancestor (e.g. `git checkout --orphan`).
        The error must not blame a shallow clone when the repo itself
        reports it isn't one.
        """
        _git(git_repo, "checkout", "-q", "--orphan", "unrelated")
        (git_repo / "other.txt").write_text("nothing to do with main\n")
        _git(git_repo, "add", "-A")
        _git(git_repo, "commit", "-q", "-m", "unrelated root commit")
        orphan_sha = _git(git_repo, "rev-parse", "HEAD").strip()
        _git(git_repo, "checkout", "-q", "main")
        main_sha = _git(git_repo, "rev-parse", "HEAD").strip()

        assert _git(git_repo, "rev-parse", "--is-shallow-repository").strip() == "false"
        with pytest.raises(ToolExecutionError) as exc_info:
            _merge_base(git_repo, main_sha, orphan_sha)
        assert "does not report itself as shallow" in str(exc_info.value)
