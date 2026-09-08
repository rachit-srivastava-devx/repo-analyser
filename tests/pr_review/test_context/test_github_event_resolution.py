"""Tests for pr_review.context.resolve_pr_context's GITHUB_EVENT_PATH
fallback (pr_review.github_event.resolve_from_github_event), exercised
end-to-end via resolve_pr_context."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import DivergedRepo

from repo_analyser.pr_review.context import resolve_pr_context


class TestGithubEventResolution:
    def test_reads_base_and_head_sha_from_event_payload(
        self, diverged_repo: DivergedRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps({
            "pull_request": {
                "base": {"sha": diverged_repo.base_sha},
                "head": {"sha": diverged_repo.head_sha},
            },
        }))
        monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
        # GITHUB_BASE_REF/GITHUB_HEAD_REF are branch names that this module
        # must NOT use (meaningless on a pull_request event's synthetic
        # merge-commit checkout) -- set to nonexistent branches so a
        # regression that reads them instead would fail loudly (a
        # ToolExecutionError from _verify_ref), not silently.
        monkeypatch.setenv("GITHUB_BASE_REF", "totally-nonexistent-branch")
        monkeypatch.setenv("GITHUB_HEAD_REF", "also-nonexistent-branch")

        ctx = resolve_pr_context(diverged_repo.repo)
        assert ctx.resolved_via == "github_event"
        assert ctx.base_sha == diverged_repo.base_sha
        assert ctx.head_sha == diverged_repo.head_sha
        assert ctx.merge_base_sha == diverged_repo.fork_sha

    def test_missing_event_path_falls_back_to_error_not_crash(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)

    def test_event_path_naming_a_nonexistent_file_falls_back_to_error(
        self, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path / "does_not_exist.json"))
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)

    def test_malformed_json_falls_back_to_error_not_crash(
        self, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text("{not valid json")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)

    def test_valid_json_missing_pull_request_key_falls_back_to_error(
        self, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps({"action": "opened"}))
        monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)

    def test_event_name_not_pull_request_is_ignored(
        self, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps({
            "pull_request": {"base": {"sha": "x"}, "head": {"sha": "y"}},
        }))
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
        with pytest.raises(ValueError, match="could not resolve"):
            resolve_pr_context(git_repo)
