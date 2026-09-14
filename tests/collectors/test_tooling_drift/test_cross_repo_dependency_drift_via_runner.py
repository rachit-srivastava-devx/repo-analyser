from __future__ import annotations

import csv
import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import run_tooling_drift


class TestCrossRepoDependencyDriftViaRunner:
    """End-to-end through the public `run_tooling_drift` entrypoint: a
    small polyrepo portfolio with a shared dependency pinned to a
    different version in one repo produces a
    tooling_drift_cross_repo_deps.csv row and a matching
    `cross_repo_dependency_versions` summary section -- never a
    `ToolingDriftRow` in tooling_drift.csv itself (see
    cross_repo_dependency_drift.py's row-shape decision)."""

    def test_polyrepo_with_one_lagging_dependency_version(self, tmp_path: Path) -> None:
        svc_a = _mkrepo(tmp_path, "svc-a")
        svc_b = _mkrepo(tmp_path, "svc-b")
        svc_c = _mkrepo(tmp_path, "svc-c")
        for repo in (svc_a, svc_b):
            (repo / "package.json").write_text('{"dependencies": {"lodash": "^4.17.0"}}')
        (svc_c / "package.json").write_text('{"dependencies": {"lodash": "^3.0.0"}}')

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_tooling_drift([svc_a, svc_b, svc_c], out_dir)

        # The main per-repo CSV never gets a row for this dimension.
        main_rows = list(csv.DictReader(open(out_path)))
        assert not any(r["config_kind"] == "cross_repo_dependency_version" for r in main_rows)

        deps_csv = out_dir / "tooling_drift_cross_repo_deps.csv"
        assert deps_csv.is_file()
        dep_rows = list(csv.DictReader(open(deps_csv)))
        assert len(dep_rows) == 1
        assert dep_rows[0]["dependency_name"] == "lodash"
        assert dep_rows[0]["ecosystem"] == "package.json"
        assert dep_rows[0]["repo_count"] == "3"
        assert "svc-c" in dep_rows[0]["repos_by_version"]

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        pkg_summary = summary["cross_repo_dependency_versions"]["package.json"]
        assert pkg_summary["repos_compared"] == 3
        assert pkg_summary["dependencies_compared"] == 1
        assert pkg_summary["dependencies_drifted"] == 1
        assert pkg_summary["skipped_reason"] == ""
        go_summary = summary["cross_repo_dependency_versions"]["go.mod"]
        assert go_summary["skipped_reason"] != ""  # no repo has a root go.mod at all

    def test_two_repo_portfolio_with_no_manifests_skips_both_ecosystems(self, tmp_path: Path) -> None:
        a = _mkrepo(tmp_path, "a")
        b = _mkrepo(tmp_path, "b")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        run_tooling_drift([a, b], out_dir)

        deps_csv = out_dir / "tooling_drift_cross_repo_deps.csv"
        assert deps_csv.is_file()
        assert list(csv.DictReader(open(deps_csv))) == []

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        for eco_summary in summary["cross_repo_dependency_versions"].values():
            assert eco_summary["skipped_reason"] != ""
