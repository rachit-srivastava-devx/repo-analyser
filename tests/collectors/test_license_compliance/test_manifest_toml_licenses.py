from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.license_compliance.manifest_licenses import (
    collect_manifest_declared_licenses,
)

from ._license_compliance_helpers import _git_repo


class TestPyprojectToml:
    def test_pep621_plain_string_license(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text('[project]\nname = "x"\nlicense = "MIT"\n')
        assert collect_manifest_declared_licenses(repo) == ["MIT"]

    def test_pep621_table_text_form(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text('[project]\nname = "x"\nlicense = { text = "MIT" }\n')
        assert collect_manifest_declared_licenses(repo) == ["MIT"]

    def test_falls_back_to_tool_poetry_license(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text('[tool.poetry]\nname = "x"\nlicense = "Apache-2.0"\n')
        assert collect_manifest_declared_licenses(repo) == ["Apache-2.0"]

    def test_malformed_toml_does_not_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pyproject.toml").write_text("[[[not valid toml :::")
        assert collect_manifest_declared_licenses(repo) == []


class TestCargoToml:
    def test_package_license(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Cargo.toml").write_text('[package]\nname = "x"\nlicense = "MIT"\n')
        assert collect_manifest_declared_licenses(repo) == ["MIT"]


class TestMultipleManifestsAtOnce:
    def test_collects_from_every_manifest_present(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"license": "MIT"}))
        (repo / "Cargo.toml").write_text('[package]\nname = "x"\nlicense = "Apache-2.0"\n')
        assert collect_manifest_declared_licenses(repo) == ["MIT", "Apache-2.0"]
