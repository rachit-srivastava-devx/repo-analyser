"""Tests for pr_review.context.resolve_pr_context (base/head precedence,
merge_base, warning on reversed refs)."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import DivergedRepo

from repo_analyser.core.util import ToolExecutionError
from repo_analyser.pr_review.context import resolve_pr_context
from repo_analyser.pr_review.ref_resolution import _verify_ref


class TestResolvePrContext:
    def test_explicit_base_and_head(self, diverged_repo: DivergedRepo) -> None:
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=diverged_repo.head_sha)
        assert ctx.resolved_via == "explicit"
        assert ctx.repo == diverged_repo.repo.name
        assert ctx.base_sha == diverged_repo.base_sha
        assert ctx.head_sha == diverged_repo.head_sha
        assert ctx.merge_base_sha == diverged_repo.fork_sha
        assert ctx.commits_in_range == 2
        assert ctx.warning is None

    def test_only_base_given_raises_naming_head_as_missing(self, diverged_repo: DivergedRepo) -> None:
        with pytest.raises(ValueError, match="head"):
            resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=None)

    def test_only_head_given_raises_naming_base_as_missing(self, diverged_repo: DivergedRepo) -> None:
        with pytest.raises(ValueError, match="base"):
            resolve_pr_context(diverged_repo.repo, base=None, head=diverged_repo.head_sha)

    def test_invalid_explicit_ref_raises_tool_execution_error(self, git_repo: Path) -> None:
        with pytest.raises(ToolExecutionError):
            resolve_pr_context(git_repo, base="nonexistent-ref", head="HEAD")

    def test_neither_explicit_nor_ci_env_raises_naming_whats_missing(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)

    def test_base_equals_head_is_a_valid_zero_commit_range(self, git_repo: Path) -> None:
        head_sha = _verify_ref(git_repo, "HEAD")
        ctx = resolve_pr_context(git_repo, base=head_sha, head=head_sha)
        assert ctx.commits_in_range == 0
        assert ctx.merge_base_sha == head_sha
        assert ctx.warning is None

    def test_reversed_refs_sets_warning_instead_of_silent_empty_diff(
        self, diverged_repo: DivergedRepo,
    ) -> None:
        # The user meant --base fork_sha --head head_sha but swapped the
        # flags. head (fork_sha) really is an ancestor of base (head_sha),
        # so merge_base_sha == head_sha and the range is empty -- but for a
        # completely different, much more mundane reason than "no changes".
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.head_sha, head=diverged_repo.fork_sha)
        assert ctx.merge_base_sha == ctx.head_sha == diverged_repo.fork_sha
        assert ctx.commits_in_range == 0
        assert ctx.warning is not None
        assert "ancestor" in ctx.warning or "swapped" in ctx.warning

    def test_genuinely_diverged_refs_do_not_spuriously_warn(self, diverged_repo: DivergedRepo) -> None:
        # Sanity check that the reversed-refs warning is not just always on:
        # a real, correctly-ordered diverged pair must NOT warn.
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=diverged_repo.head_sha)
        assert ctx.warning is None
