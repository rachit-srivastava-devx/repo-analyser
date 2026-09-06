from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestContentTypeLibraryPackage:
    def test_package_json_with_exports_no_dockerfile(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"name": "x", "exports": "./index.js"}))
        result = analyze_repo(repo, [repo])
        assert "library_package" in result.content_types

    def test_pyproject_build_system_table(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text("[build-system]\nrequires = [\"setuptools\"]\n")
        assert "library_package" in analyze_repo(repo, [repo]).content_types


class TestContentTypeInfraGitops:
    def test_terraform_file(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "main.tf").write_text("resource \"null_resource\" \"x\" {}\n")
        assert "infra_gitops" in analyze_repo(repo, [repo]).content_types

    def test_helm_chart_yaml(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Chart.yaml").write_text("apiVersion: v2\nname: x\nversion: 0.1.0\n")
        assert "infra_gitops" in analyze_repo(repo, [repo]).content_types

    def test_kustomization_yaml(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "kustomization.yaml").write_text("resources:\n- deployment.yaml\n")
        assert "infra_gitops" in analyze_repo(repo, [repo]).content_types


class TestContentTypeDocsRepo:
    def test_majority_markdown_files(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        for i in range(5):
            (repo / f"doc{i}.md").write_text("# doc\n")
        (repo / "one.py").write_text("x = 1\n")
        assert "docs_repo" in analyze_repo(repo, [repo]).content_types

    def test_mkdocs_yml_marker(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "mkdocs.yml").write_text("site_name: x\n")
        assert "docs_repo" in analyze_repo(repo, [repo]).content_types


class TestContentTypeDeveloperTools:
    def test_package_json_bin_field(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"name": "x", "bin": {"x": "./cli.js"}}))
        assert "developer_tools" in analyze_repo(repo, [repo]).content_types

    def test_go_cmd_directory(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "cmd").mkdir()
        assert "developer_tools" in analyze_repo(repo, [repo]).content_types

    def test_pyproject_project_scripts(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text("[project.scripts]\nx = \"x:main\"\n")
        assert "developer_tools" in analyze_repo(repo, [repo]).content_types
