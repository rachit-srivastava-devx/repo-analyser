from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.license_compliance import analyze_repo

from ._license_compliance_helpers import MIT_TEXT, _git_repo


class TestNoLicenseNoManifests:
    def test_all_fields_report_absence_cleanly(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        result = analyze_repo(repo)
        assert result.license_file == ""
        assert result.license_id == "unknown"
        assert result.manifest_declared_licenses == ""
        assert result.license_mismatch is False
        assert result.has_dependencies_no_license is False


class TestLicenseMismatch:
    def test_matching_declared_license_is_not_a_mismatch(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        (repo / "package.json").write_text(json.dumps({"license": "MIT"}))
        result = analyze_repo(repo)
        assert result.license_id == "MIT"
        assert result.license_mismatch is False

    def test_disagreeing_declared_license_is_a_mismatch(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        (repo / "package.json").write_text(json.dumps({"license": "Apache-2.0"}))
        result = analyze_repo(repo)
        assert result.license_id == "MIT"
        assert result.license_mismatch is True

    def test_see_license_in_pointer_is_excluded_from_mismatch_comparison(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        (repo / "package.json").write_text(json.dumps({"license": "SEE LICENSE IN LICENSE"}))
        result = analyze_repo(repo)
        assert result.license_mismatch is False

    def test_unknown_license_id_never_reports_a_mismatch(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text("Some bespoke custom license text nobody recognizes.")
        (repo / "package.json").write_text(json.dumps({"license": "MIT"}))
        result = analyze_repo(repo)
        assert result.license_id == "unknown"
        assert result.license_mismatch is False


class TestHasDependenciesNoLicense:
    def test_manifest_present_but_no_license_file(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        result = analyze_repo(repo)
        assert result.has_dependencies_no_license is True

    def test_manifest_present_with_license_file_is_false(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        (repo / "go.mod").write_text("module example.com/x\n")
        result = analyze_repo(repo)
        assert result.has_dependencies_no_license is False

    def test_no_manifest_and_no_license_is_false(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        result = analyze_repo(repo)
        assert result.has_dependencies_no_license is False
