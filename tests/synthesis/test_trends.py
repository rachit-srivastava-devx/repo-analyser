from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.core.util import write_json
from repo_analyser.synthesis.trends import (
    BASELINE_FILENAME,
    TrendRow,
    _classify,
    compare_to_baseline,
    extract_metrics,
    run_trends,
)


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
