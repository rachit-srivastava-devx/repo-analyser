"""Tests for pr_review.ref_resolution._verify_ref."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import _git

from repo_analyser.core.util import ToolExecutionError
from repo_analyser.pr_review.ref_resolution import _verify_ref


class TestVerifyRef:
    def test_valid_branch_name_resolves_to_full_sha(self, git_repo: Path) -> None:
        sha = _verify_ref(git_repo, "main")
        assert len(sha) == 40
        assert sha == _git(git_repo, "rev-parse", "HEAD").strip()

    def test_invalid_ref_raises_tool_execution_error(self, git_repo: Path) -> None:
        with pytest.raises(ToolExecutionError):
            _verify_ref(git_repo, "not-a-real-ref-xyz")

    def test_ref_shaped_like_a_flag_is_not_parsed_as_one(self, git_repo: Path) -> None:
        # The trailing `--` in `git rev-parse --verify <ref> --` exists so a
        # ref crafted to look like a flag (plausible on a fork PR, which is
        # attacker-controlled input per AGENTS.md §3 rung 8) is looked up as
        # a revision -- and fails cleanly -- rather than parsed as an
        # option. This must raise the same clean "not a ref" error, not
        # behave as if `--upload-pack` were a real git flag.
        with pytest.raises(ToolExecutionError) as exc_info:
            _verify_ref(git_repo, "--upload-pack=touch /tmp/pwned")
        assert exc_info.value.returncode != 0
