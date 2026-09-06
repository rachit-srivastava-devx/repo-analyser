from __future__ import annotations

import csv
import json
from pathlib import Path

from _microservices_topology_helpers import _write_compose

from repo_analyser.collectors.microservices_topology import run_microservices_topology


class TestRunMicroservicesTopology:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_microservices_topology([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()
        _write_compose(repo_b, {"web": {"depends_on": ["db"]}, "db": {}})
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_microservices_topology([repo_a, repo_b], out_dir)
        rows = {r["repo"]: r for r in csv.DictReader(open(out_path))}
        assert set(rows["repo-a"].keys()) == {
            "repo", "service_count", "has_dependency_cycle", "cycle_detail",
            "has_service_mesh", "mesh_kind", "has_network_policy_default_deny",
            "has_canary_rollout_config", "resilience_libs_detected", "skip_reason",
        }
        assert rows["repo-a"]["skip_reason"] != ""
        assert rows["repo-b"]["service_count"] == "2"
        assert rows["repo-b"]["has_dependency_cycle"] == "False"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        _write_compose(repo_a, {"a": {"depends_on": ["b"]}, "b": {"depends_on": ["a"]}})
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_microservices_topology([repo_a], out_dir)
        summary = json.loads((out_dir / "microservices_topology_summary.json").read_text())
        assert summary["repos_total"] == 1
        assert summary["repos_analyzed"] == 1
        assert summary["repos_with_dependency_cycle"] == 1
