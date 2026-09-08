from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.synthesis.synthesize import WEIGHTS, _norm, run_synthesize


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class TestNorm:
    def test_empty_returns_empty(self) -> None:
        assert _norm({}) == {}

    def test_all_equal_values_returns_all_zero_not_div_by_zero(self) -> None:
        assert _norm({"a": 5, "b": 5, "c": 5}) == {"a": 0.0, "b": 0.0, "c": 0.0}

    def test_min_max_scaling(self) -> None:
        result = _norm({"a": 0, "b": 5, "c": 10})
        assert result == {"a": 0.0, "b": 0.5, "c": 1.0}

    def test_single_value_is_zero(self) -> None:
        assert _norm({"a": 42}) == {"a": 0.0}


class TestRunSynthesize:
    def test_missing_input_csvs_do_not_crash(self, tmp_path: Path) -> None:
        out_path = run_synthesize(["repo-a", "repo-b"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 2
        # no ci_gates.csv at all defaults every repo to "no CI gate" (1.0,
        # the risk-assuming default for missing data, not 0) -- with no
        # other CSV present to differentiate them, both repos land on the
        # same score rather than crashing or silently guessing a ranking.
        assert rows[0]["risk_score"] == rows[1]["risk_score"]
        assert float(rows[0]["risk_score"]) == WEIGHTS["no_ci_gate"]

    def test_repo_with_more_escapes_ranks_higher(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "escapes.csv", [
            {"repo": "risky", "fix_sha": "a", "fix_date": "2025-01-01", "file": "x.py",
             "introducing_sha": "b", "introducing_date": "2024-01-01", "latency_days": "300"},
            {"repo": "risky", "fix_sha": "c", "fix_date": "2025-01-01", "file": "y.py",
             "introducing_sha": "d", "introducing_date": "2024-01-01", "latency_days": "300"},
        ])
        out_path = run_synthesize(["risky", "safe"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert rows[0]["repo"] == "risky"
        assert float(rows[0]["risk_score"]) > float(rows[1]["risk_score"])

    def test_ci_gate_missing_contributes_to_score(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "ci_gates.csv", [
            {"repo": "no-ci", "has_ci_config": "False", "workflow_count": "0",
             "workflow_files": "", "any_workflow_runs_tests": "False",
             "all_workflows_deploy_only": "False", "triggers": ""},
            {"repo": "has-ci", "has_ci_config": "True", "workflow_count": "1",
             "workflow_files": "ci.yml", "any_workflow_runs_tests": "True",
             "all_workflows_deploy_only": "False", "triggers": "push"},
        ])
        out_path = run_synthesize(["no-ci", "has-ci"], tmp_path)
        rows = {r["repo"]: r for r in csv.DictReader(open(out_path))}
        assert rows["no-ci"]["ci_gate_missing"] == "True"
        assert rows["has-ci"]["ci_gate_missing"] == "False"
        assert float(rows["no-ci"]["risk_score"]) > float(rows["has-ci"]["risk_score"])

    def test_test_failure_rate_uses_ratio_not_raw_count(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "testquality_runs.csv", [
            {"repo": "small-suite", "script_used": "test", "ran": "True", "exit_code": "1",
             "runner_detected": "vitest", "tests_passed": "1", "tests_failed": "1", "tests_total": "2",
             "duration_s": "1.0", "skip_reason": "", "node_version_used": "v20", "failure_mode": ""},
        ])
        out_path = run_synthesize(["small-suite"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert rows[0]["test_failure_rate"] == "0.5"

    def test_zero_total_tests_is_zero_failure_rate_not_div_by_zero(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "testquality_runs.csv", [
            {"repo": "no-tests", "script_used": "", "ran": "False", "exit_code": "-1",
             "runner_detected": "", "tests_passed": "0", "tests_failed": "0", "tests_total": "0",
             "duration_s": "0.0", "skip_reason": "no script", "node_version_used": "", "failure_mode": ""},
        ])
        out_path = run_synthesize(["no-tests"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert rows[0]["test_failure_rate"] == "0.0"

    def test_hotspot_sum_takes_top_5_only(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "complexity_hotspots.csv", [
            {"repo": "r", "file": f"f{i}.py", "total_ccn": "1", "max_ccn": "1",
             "function_count": "1", "total_nloc": "10", "n_revs": "1", "hotspot_score": str(score)}
            for i, score in enumerate([100, 90, 80, 70, 60, 50, 40])  # 7 files, only top 5 count
        ])
        out_path = run_synthesize(["r"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert float(rows[0]["top5_hotspot_sum"]) == 100 + 90 + 80 + 70 + 60

    def test_writes_risk_weights_json_matching_module_constant(self, tmp_path: Path) -> None:
        run_synthesize(["r"], tmp_path)
        weights = json.loads((tmp_path / "risk_weights.json").read_text())
        assert sum(weights.values()) == 1.0

    def test_repo_not_in_any_csv_still_gets_a_zero_row(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "escapes.csv", [
            {"repo": "other-repo", "fix_sha": "a", "fix_date": "2025-01-01", "file": "x.py",
             "introducing_sha": "b", "introducing_date": "2024-01-01", "latency_days": "1"},
        ])
        out_path = run_synthesize(["untouched-repo"], tmp_path)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert rows[0]["repo"] == "untouched-repo"
        assert rows[0]["escape_count"] == "0"

    def test_empty_repo_names_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_path = run_synthesize([], tmp_path)
        assert out_path.read_text().splitlines() == [
            "repo,risk_score,escape_count,top5_hotspot_sum,exact_dup_file_count,"
            "ci_gate_missing,test_failure_rate,security_findings,bus_factor_top_author_share"
        ]
