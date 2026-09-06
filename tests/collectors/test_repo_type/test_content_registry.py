from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestContentTypeDataPipelineEtl:
    def test_dbt_project_yml(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "dbt_project.yml").write_text("name: x\n")
        assert "data_pipeline_etl" in analyze_repo(repo, [repo]).content_types

    def test_dags_directory(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "dags").mkdir()
        assert "data_pipeline_etl" in analyze_repo(repo, [repo]).content_types


class TestContentTypeBrowserExtension:
    def test_manifest_json_with_manifest_version(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "manifest.json").write_text(json.dumps({"manifest_version": 3, "name": "x"}))
        assert "browser_extension" in analyze_repo(repo, [repo]).content_types

    def test_manifest_json_without_manifest_version_does_not_match(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "manifest.json").write_text(json.dumps({"name": "x"}))
        assert "browser_extension" not in analyze_repo(repo, [repo]).content_types


class TestContentTypeGameEngineOrMultiagent:
    def test_unity_assets_and_projectsettings(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Assets").mkdir()
        (repo / "ProjectSettings").mkdir()
        assert "game_engine_or_multiagent" in analyze_repo(repo, [repo]).content_types

    def test_langgraph_dependency(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "requirements.txt").write_text("langgraph==0.1.0\n")
        assert "game_engine_or_multiagent" in analyze_repo(repo, [repo]).content_types
