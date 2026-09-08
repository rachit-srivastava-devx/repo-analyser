from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.license_compliance import analyze_repo

from ._license_compliance_helpers import (
    BLANK_LINE_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT,
    HEADING_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT,
    LEADING_APACHE_MENTION_TRAILING_MPL_BLOCK_TEXT,
    MIT_TEXT,
    NO_SEPARATOR_LINE_ADJACENT_APACHE_MENTION_THEN_MPL_BLOCK_TEXT,
    THREE_WAY_CONTAMINATION_TEXT,
    _git_repo,
)


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


class TestSpdxCrossContaminationAtCollectorLevel:
    """Full analyze_repo() collector-level reproduction of the three
    known-hard cases plus this attempt's own self-invented adversarial
    cases, over a real on-disk LICENSE file in a real git repo -- not
    just match_spdx_id() called directly."""

    def test_rule_line_separated_counter_example_resolves_to_mpl(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(LEADING_APACHE_MENTION_TRAILING_MPL_BLOCK_TEXT)
        assert analyze_repo(repo).license_id == "MPL-2.0"

    def test_blank_line_separated_variant_resolves_to_mpl(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(BLANK_LINE_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT)
        assert analyze_repo(repo).license_id == "MPL-2.0"

    def test_heading_separated_variant_resolves_to_mpl(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(HEADING_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT)
        assert analyze_repo(repo).license_id == "MPL-2.0"

    def test_no_separator_line_adjacent_variant_resolves_to_mpl(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(
            NO_SEPARATOR_LINE_ADJACENT_APACHE_MENTION_THEN_MPL_BLOCK_TEXT
        )
        assert analyze_repo(repo).license_id == "MPL-2.0"

    def test_three_way_contamination_resolves_to_mpl(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(THREE_WAY_CONTAMINATION_TEXT)
        assert analyze_repo(repo).license_id == "MPL-2.0"


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
