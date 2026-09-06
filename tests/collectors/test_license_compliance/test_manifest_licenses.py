from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.license_compliance.manifest_licenses import (
    collect_manifest_declared_licenses,
)

from ._license_compliance_helpers import _git_repo


class TestPackageJson:
    def test_string_license_field(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"name": "x", "license": "MIT"}))
        assert collect_manifest_declared_licenses(repo) == ["MIT"]

    def test_object_type_license_field(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text(json.dumps({"license": {"type": "ISC", "url": "x"}}))
        assert collect_manifest_declared_licenses(repo) == ["ISC"]

    def test_malformed_json_does_not_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "package.json").write_text("{not valid json")
        assert collect_manifest_declared_licenses(repo) == []


class TestComposerJson:
    def test_string_license(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "composer.json").write_text(json.dumps({"license": "MIT"}))
        assert collect_manifest_declared_licenses(repo) == ["MIT"]

    def test_array_license_dual_licensed(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "composer.json").write_text(json.dumps({"license": ["MIT", "Apache-2.0"]}))
        assert collect_manifest_declared_licenses(repo) == ["MIT OR Apache-2.0"]


class TestNoManifestsAtAll:
    def test_returns_empty_list(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        assert collect_manifest_declared_licenses(repo) == []
