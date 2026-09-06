from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.license_compliance import run_license_compliance

from ._license_compliance_helpers import MIT_TEXT, _git_repo


class TestRunLicenseCompliance:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_license_compliance([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_license_compliance([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "license_file", "license_id", "manifest_declared_licenses",
            "license_mismatch", "has_dependencies_no_license", "detection_notes",
        }
        assert rows[0]["license_id"] == "MIT"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = _git_repo(tmp_path / "repo-a")
        (repo_a / "LICENSE").write_text(MIT_TEXT)
        repo_b = _git_repo(tmp_path / "repo-b")
        (repo_b / "requirements.txt").write_text("requests==2.0.0\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_license_compliance([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "license_compliance_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["license_id_counts"]["MIT"] == 1
        assert summary["license_id_counts"]["unknown"] == 1
        assert summary["repos_with_dependencies_no_license"] == 1
        assert summary["repos_with_mismatch"] == 0
