from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestPrimaryTypeDefault:
    def test_empty_repo_defaults_to_single_repo(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "single_repo"
        assert result.content_types == ""
        assert result.signals_matched  # never asserts with zero recorded evidence

    def test_bare_package_json_alone_is_single_repo(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"name": "x", "version": "1.0.0"}))
        assert analyze_repo(repo, [repo]).primary_type == "single_repo"


class TestPrimaryTypeMonorepo:
    def test_nx_json_at_root(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "nx.json").write_text("{}")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "monorepo"
        assert "nx.json" in result.signals_matched

    def test_bazel_workspace_file(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "WORKSPACE.bazel").write_text("")
        assert analyze_repo(repo, [repo]).primary_type == "monorepo"

    def test_unmanaged_monorepo_multiple_sibling_manifests(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text("{}")
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "pyproject.toml").write_text("[project]\nname='b'\n")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "monorepo"
        assert "unmanaged" in result.detection_notes

    def test_single_sibling_manifest_is_not_enough_to_trigger_unmanaged_monorepo(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text("{}")
        assert analyze_repo(repo, [repo]).primary_type == "single_repo"
