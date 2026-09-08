"""The regression test this whole task exists to get right: a two-dot
`base..head` diff and a `merge_base..head` diff must disagree on this
fixture (proving the fixture actually exercises the bug), and
`get_changed_files` must match the correct (merge_base) side, never the
buggy (two-dot) one.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from _pr_review_helpers import _ctx
from conftest import DivergedRepo, _git

from repo_analyser.pr_review.context import resolve_pr_context
from repo_analyser.pr_review.diff import get_changed_files


class TestGetChangedFilesUsesMergeBase:
    def test_excludes_base_only_includes_head_only(self, diverged_repo: DivergedRepo) -> None:
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=diverged_repo.head_sha)
        changed = get_changed_files(diverged_repo.repo, ctx)
        paths = {cf.path for cf in changed}
        assert paths == diverged_repo.head_only_files
        assert not (paths & diverged_repo.base_only_files)

    def test_fixture_actually_exercises_the_two_dot_bug(self, diverged_repo: DivergedRepo) -> None:
        """Not testing pr_review's own code: proves the fixture itself has
        the property the task requires -- that a naive two-dot base..head
        diff WOULD wrongly include base-only files. Without this, the test
        above could pass by fixture accident (e.g. on a linear history)
        even with the two-dot bug reintroduced in get_changed_files.
        """
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{diverged_repo.base_sha}..{diverged_repo.head_sha}"],
            cwd=diverged_repo.repo, check=True, capture_output=True, text=True,
        )
        two_dot_paths = set(result.stdout.split())
        assert diverged_repo.base_only_files & two_dot_paths

    def test_correct_status_and_line_counts_for_head_only_file(self, diverged_repo: DivergedRepo) -> None:
        ctx = resolve_pr_context(diverged_repo.repo, base=diverged_repo.base_sha, head=diverged_repo.head_sha)
        changed = get_changed_files(diverged_repo.repo, ctx)
        assert len(changed) == 1
        cf = changed[0]
        assert cf.path == "feature.txt"
        assert cf.status == "A"
        assert cf.old_path is None
        assert cf.additions == 2
        assert cf.deletions == 0
        assert cf.added_line_ranges == [(1, 2)]

    def test_base_equals_head_returns_empty_list(self, git_repo: Path) -> None:
        head_sha = _git(git_repo, "rev-parse", "HEAD").strip()
        ctx = _ctx(head_sha, head_sha)
        assert get_changed_files(git_repo, ctx) == []
