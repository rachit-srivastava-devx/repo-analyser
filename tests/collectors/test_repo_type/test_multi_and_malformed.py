from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestMultipleContentTypesAtOnce:
    def test_monorepo_that_also_ships_ml_pipeline(self, tmp_path: Path) -> None:
        # primary_type and content_types are independent axes -- a repo can
        # be a monorepo AND have an ML content signal simultaneously.
        repo = _git_repo(tmp_path / "repo")
        (repo / "nx.json").write_text("{}")
        (repo / "analysis.ipynb").write_text("{}")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "monorepo"
        assert "ml_data_science" in result.content_types


class TestMalformedInputHandling:
    def test_malformed_package_json_does_not_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text("{not valid json")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "single_repo"

    def test_malformed_docker_compose_yaml_does_not_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "docker-compose.yml").write_text(":::not valid yaml:::\n  -\n")
        result = analyze_repo(repo, [repo])
        assert result.primary_type in ("single_repo", "monorepo", "microservices", "polyrepo", "meta_repo")
