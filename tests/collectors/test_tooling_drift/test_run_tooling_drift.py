from __future__ import annotations

import csv
import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import run_tooling_drift


class TestRunToolingDrift:
    def test_empty_repos_writes_header_and_summary(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_tooling_drift([], out_dir)
        assert out_path.exists()
        with open(out_path) as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == [
                "repo", "config_kind", "packages_compared",
                "packages_with_drift", "drift_detail", "skip_reason",
            ]
            assert list(reader) == []
        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        assert summary["repos_total"] == 0
        assert summary["repos_with_drift"] == 0

    def test_single_manifest_repo_writes_skip_row_with_repo_column(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "package.json").write_text("{}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_tooling_drift([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert rows[0]["repo"] == repo.name
        assert rows[0]["config_kind"] == "none"
        assert rows[0]["skip_reason"]

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        assert summary["repos_skipped_insufficient_manifests"] == 1
        assert summary["repos_with_drift"] == 0

    def test_drifted_repo_appears_in_csv_and_summary(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_tooling_drift([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert rows[0]["repo"] == repo.name
        assert rows[0]["config_kind"] == "dependency_version"

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        assert summary["repos_with_drift"] == 1
        assert summary["drift_rows_by_kind"]["dependency_version"] == 1

    def test_multiple_repos_are_independent(self, tmp_path: Path) -> None:
        drifted = _mkrepo(tmp_path, "drifted")
        (drifted / "pkg-a").mkdir()
        (drifted / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (drifted / "pkg-b").mkdir()
        (drifted / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))

        single = _mkrepo(tmp_path, "single")
        (single / "package.json").write_text("{}")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_tooling_drift([drifted, single], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        by_repo = {r["repo"]: r for r in rows}
        assert by_repo["drifted"]["config_kind"] == "dependency_version"
        assert by_repo["single"]["config_kind"] == "none"
