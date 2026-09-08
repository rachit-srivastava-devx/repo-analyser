from __future__ import annotations

import csv
import json
from pathlib import Path

from _observability_helpers import write_files

from repo_analyser.collectors.observability.runner import run_observability


class TestRunObservability:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_observability([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo_a = write_files(tmp_path / "repo-a", {})
        repo_b = write_files(tmp_path / "repo-b", {
            "package.json": json.dumps({"dependencies": {"winston": "^3.0.0"}}),
        })
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_observability([repo_a, repo_b], out_dir)
        rows = {r["repo"]: r for r in csv.DictReader(open(out_path))}
        assert list(rows["repo-a"].keys()) == [
            "repo", "has_structured_logging", "logging_lib", "has_metrics_lib", "metrics_lib",
            "has_tracing", "tracing_lib", "has_k8s_health_probes", "skip_reason",
        ]
        assert rows["repo-a"]["has_structured_logging"] == "False"
        assert rows["repo-a"]["skip_reason"] != ""
        assert rows["repo-b"]["has_structured_logging"] == "True"
        assert rows["repo-b"]["logging_lib"] == "winston"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = write_files(tmp_path / "repo-a", {"package.json": json.dumps({
            "dependencies": {"winston": "^3.0.0", "prom-client": "^15.0.0", "@opentelemetry/api": "^1.7.0"},
        })})
        repo_b = write_files(tmp_path / "repo-b", {})
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_observability([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "observability_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["repos_with_structured_logging"] == 1
        assert summary["repos_with_metrics_lib"] == 1
        assert summary["repos_with_tracing"] == 1
        assert summary["repos_with_k8s_health_probes"] == 0
