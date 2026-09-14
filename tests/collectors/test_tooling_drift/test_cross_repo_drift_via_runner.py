from __future__ import annotations

import csv
import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import run_tooling_drift


class TestCrossRepoDriftViaRunner:
    """End-to-end through the public `run_tooling_drift` entrypoint: a
    small polyrepo portfolio where one repo forks its eslint config from
    the other two produces a cross_repo_eslint row and a matching
    `cross_repo_canonical` summary section."""

    def test_polyrepo_with_one_forked_eslint_config(self, tmp_path: Path) -> None:
        canonical_a = _mkrepo(tmp_path, "svc-canonical-a")
        canonical_b = _mkrepo(tmp_path, "svc-canonical-b")
        forked = _mkrepo(tmp_path, "svc-forked")
        for repo in (canonical_a, canonical_b, forked):
            (repo / "package.json").write_text("{}")
        (canonical_a / ".eslintrc.json").write_text('{"extends": "airbnb"}')
        (canonical_b / ".eslintrc.json").write_text('{"extends": "airbnb"}')
        (forked / ".eslintrc.json").write_text('{"extends": "standard"}')

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_tooling_drift([canonical_a, canonical_b, forked], out_dir)

        rows = list(csv.DictReader(open(out_path)))
        cross_rows = [r for r in rows if r["config_kind"] == "cross_repo_eslint"]
        assert len(cross_rows) == 1
        assert cross_rows[0]["repo"] == "svc-forked"
        assert cross_rows[0]["packages_compared"] == "3"
        assert cross_rows[0]["packages_with_drift"] == "1"

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        eslint_summary = summary["cross_repo_canonical"]["cross_repo_eslint"]
        assert eslint_summary["repos_compared"] == 3
        assert eslint_summary["repos_drifted"] == 1
        assert eslint_summary["skipped_reason"] == ""
        assert summary["drift_rows_by_kind"]["cross_repo_eslint"] == 1

    def test_two_repo_portfolio_with_no_manifests_skips_all_cross_repo_kinds(self, tmp_path: Path) -> None:
        a = _mkrepo(tmp_path, "a")
        b = _mkrepo(tmp_path, "b")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_tooling_drift([a, b], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert not any(r["config_kind"].startswith("cross_repo_") for r in rows)

        summary = json.loads((out_dir / "tooling_drift_summary.json").read_text())
        for kind_summary in summary["cross_repo_canonical"].values():
            assert kind_summary["skipped_reason"] != ""
