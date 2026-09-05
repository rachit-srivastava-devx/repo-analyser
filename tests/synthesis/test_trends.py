from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.core.util import write_json
from repo_analyser.synthesis.trends import (
    BASELINE_FILENAME,
    PER_REPO_BASELINE_FILENAME,
    TrendRow,
    _classify,
    compare_per_repo_to_baseline,
    compare_to_baseline,
    extract_metrics,
    extract_per_repo_metrics,
    run_trends,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class TestExtractMetrics:
    def test_missing_summary_files_all_none(self, tmp_path: Path) -> None:
        metrics = extract_metrics(tmp_path)
        assert all(v is None for v in metrics.values())

    def test_reads_top_level_field(self, tmp_path: Path) -> None:
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 3})
        assert extract_metrics(tmp_path)["secrets_found"] == 3

    def test_reads_nested_field(self, tmp_path: Path) -> None:
        write_json(tmp_path / "duplication_summary.json", {"portfolio_stats": {"percentage": 63.5}})
        assert extract_metrics(tmp_path)["duplication_percentage"] == 63.5

    def test_null_json_field_is_none_not_a_crash(self, tmp_path: Path) -> None:
        write_json(tmp_path / "mutation_summary.json", {"mean_mutation_score": None})
        assert extract_metrics(tmp_path)["mean_mutation_score"] is None

    def test_non_numeric_field_is_none_not_a_crash(self, tmp_path: Path) -> None:
        # a malformed or differently-shaped summary shouldn't raise --
        # just report "couldn't read this metric," per this field's
        # own real observed shape (a dict, not a number) elsewhere in
        # the same file (skip_reasons is a dict, not a metric).
        write_json(tmp_path / "testquality_summary.json", {"repos_all_tests_passing": {"not": "a number"}})
        assert extract_metrics(tmp_path)["repos_all_tests_passing"] is None

    def test_malformed_json_is_none_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "security_summary.json").write_text("{not valid json")
        assert extract_metrics(tmp_path)["secrets_found"] is None


class TestClassify:
    def test_no_current_data_is_no_data(self) -> None:
        assert _classify("secrets_found", 5, None) == TrendRow("secrets_found", 5, None, None, "no_data")

    def test_no_baseline_is_new(self) -> None:
        assert _classify("secrets_found", None, 5) == TrendRow("secrets_found", None, 5, None, "new")

    def test_unchanged(self) -> None:
        row = _classify("secrets_found", 5, 5)
        assert row.direction == "unchanged"
        assert row.delta == 0

    def test_lower_is_better_metric_going_down_is_improved(self) -> None:
        row = _classify("secrets_found", 5, 2)
        assert row.direction == "improved"
        assert row.delta == -3

    def test_lower_is_better_metric_going_up_is_regressed(self) -> None:
        row = _classify("secrets_found", 2, 5)
        assert row.direction == "regressed"
        assert row.delta == 3

    def test_higher_is_better_metric_going_up_is_improved(self) -> None:
        row = _classify("mean_mutation_score", 50.0, 66.7)
        assert row.direction == "improved"

    def test_higher_is_better_metric_going_down_is_regressed(self) -> None:
        row = _classify("mean_mutation_score", 66.7, 50.0)
        assert row.direction == "regressed"

    def test_unknown_metric_defaults_to_higher_is_better(self) -> None:
        row = _classify("some_future_metric_not_yet_categorized", 1, 2)
        assert row.direction == "improved"


class TestCompareToBaseline:
    def test_no_baseline_file_everything_is_new(self, tmp_path: Path) -> None:
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 3})
        rows = compare_to_baseline(tmp_path)
        row = next(r for r in rows if r.metric == "secrets_found")
        assert row.direction == "new"

    def test_reads_existing_baseline(self, tmp_path: Path) -> None:
        write_json(tmp_path / BASELINE_FILENAME, {"secrets_found": 5})
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 2})
        rows = compare_to_baseline(tmp_path)
        row = next(r for r in rows if r.metric == "secrets_found")
        assert row.direction == "improved"
        assert row.baseline == 5


class TestRunTrends:
    def test_first_run_writes_report_and_baseline(self, tmp_path: Path) -> None:
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 3})
        report_path = run_trends(tmp_path)
        report = json.loads(report_path.read_text())
        assert any(m["metric"] == "secrets_found" and m["direction"] == "new" for m in report["metrics"])
        baseline = json.loads((tmp_path / BASELINE_FILENAME).read_text())
        assert baseline["secrets_found"] == 3

    def test_second_run_detects_a_real_regression(self, tmp_path: Path) -> None:
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 0})
        run_trends(tmp_path)  # first run: baseline becomes 0

        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 4})
        report_path = run_trends(tmp_path)  # second run: 0 -> 4 secrets is a real regression
        report = json.loads(report_path.read_text())
        assert "secrets_found" in report["regressions"]

    def test_second_run_detects_a_real_improvement(self, tmp_path: Path) -> None:
        write_json(tmp_path / "mutation_summary.json", {"mean_mutation_score": 40.0})
        run_trends(tmp_path)

        write_json(tmp_path / "mutation_summary.json", {"mean_mutation_score": 80.0})
        report_path = run_trends(tmp_path)
        report = json.loads(report_path.read_text())
        assert "mean_mutation_score" in report["improvements"]

    def test_baseline_is_overwritten_each_run_not_accumulated(self, tmp_path: Path) -> None:
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 1})
        run_trends(tmp_path)
        write_json(tmp_path / "security_summary.json", {"total_secrets_found": 2})
        run_trends(tmp_path)
        baseline = json.loads((tmp_path / BASELINE_FILENAME).read_text())
        assert baseline["secrets_found"] == 2

    def test_repo_names_none_skips_per_repo_output_backward_compat(self, tmp_path: Path) -> None:
        run_trends(tmp_path)  # no repo_names -- old call-site shape
        assert not (tmp_path / "trend_report_per_repo.json").exists()
        assert not (tmp_path / PER_REPO_BASELINE_FILENAME).exists()

    def test_repo_names_given_writes_per_repo_report_and_baseline(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "risk_ranking.csv", [
            {"repo": "r", "risk_score": "0.5", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "False", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
        ])
        run_trends(tmp_path, ["r"])
        report = json.loads((tmp_path / "trend_report_per_repo.json").read_text())
        assert "r" in report
        assert any(m["metric"] == "risk_score" and m["direction"] == "new" for m in report["r"]["metrics"])
        baseline = json.loads((tmp_path / PER_REPO_BASELINE_FILENAME).read_text())
        assert baseline["r"]["risk_score"] == 0.5


class TestExtractPerRepoMetrics:
    def test_missing_csvs_all_none(self, tmp_path: Path) -> None:
        metrics = extract_per_repo_metrics(tmp_path, ["r"])
        assert all(v is None for v in metrics["r"].values())

    def test_pulls_real_values_from_risk_ranking(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "risk_ranking.csv", [
            {"repo": "r", "risk_score": "0.7", "escape_count": "3", "top5_hotspot_sum": "100",
             "exact_dup_file_count": "2", "ci_gate_missing": "True", "test_failure_rate": "0.1",
             "security_findings": "5", "bus_factor_top_author_share": "0.9"},
        ])
        metrics = extract_per_repo_metrics(tmp_path, ["r"])["r"]
        assert metrics["risk_score"] == 0.7
        assert metrics["security_findings"] == 5.0

    def test_mutation_score_only_counted_when_ran_true(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "mutation_results.csv", [
            {"repo": "r", "file_mutated": "", "total_mutants": "0", "killed": "0", "survived": "0",
             "no_coverage": "0", "timeout": "0", "mutation_score": "0", "ran": "False",
             "skip_reason": "no passing suite", "suspicious": "0", "segfault": "0"},
        ])
        metrics = extract_per_repo_metrics(tmp_path, ["r"])["r"]
        assert metrics["mutation_score"] is None

    def test_repo_not_in_csv_gets_all_none(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "risk_ranking.csv", [
            {"repo": "other", "risk_score": "0.5", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "False", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
        ])
        metrics = extract_per_repo_metrics(tmp_path, ["untouched"])["untouched"]
        assert all(v is None for v in metrics.values())


class TestComparePerRepoToBaseline:
    def test_real_regression_detected_for_one_repo_not_the_whole_portfolio(self, tmp_path: Path) -> None:
        write_json(tmp_path / PER_REPO_BASELINE_FILENAME, {"risky": {"risk_score": 0.2}, "safe": {"risk_score": 0.1}})
        _write_csv(tmp_path / "risk_ranking.csv", [
            {"repo": "risky", "risk_score": "0.9", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "False", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
            {"repo": "safe", "risk_score": "0.1", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "False", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
        ])
        result = compare_per_repo_to_baseline(tmp_path, ["risky", "safe"])
        risky_directions = {r.metric: r.direction for r in result["risky"]}
        safe_directions = {r.metric: r.direction for r in result["safe"]}
        assert risky_directions["risk_score"] == "regressed"
        assert safe_directions["risk_score"] == "unchanged"
