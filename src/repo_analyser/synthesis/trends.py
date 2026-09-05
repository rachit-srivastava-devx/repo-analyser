"""Self-learning trend comparison: diff this run's key portfolio metrics
against a saved baseline from a prior run against the same --out
directory, flagging real regressions and improvements automatically --
rather than a human eyeballing two runs side by side, which is what every
before/after comparison this tool has produced so far actually was (see
docs/METHODOLOGY.md #35).

Reads other collectors' already-written *_summary.json files -- computes
nothing new, matches this subpackage's own "no external tool calls, reads
every collector's output" rule (docs/ARCHITECTURE.md). A curated, real
subset of fields, not every field of every summary -- picked because each
one answers "did this portfolio get healthier or worse," not because it
was the easiest field to grab.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..core.util import read_json, write_json

BASELINE_FILENAME = "trend_baseline.json"

# metric key -> True if a HIGHER number is the improvement (e.g. more
# passing repos is good); False if a LOWER number is the improvement
# (e.g. fewer secrets found is good). Drives _classify()'s regression/
# improvement call -- getting this backwards for even one metric would
# silently invert its verdict, so every entry here is deliberate, not a
# default.
METRIC_DIRECTIONS: dict[str, bool] = {
    "secrets_found": False,
    "semgrep_findings": False,
    "cve_findings": False,
    "outdated_packages": False,
    "lint_errors": False,
    "lint_warnings": False,
    "mean_mutation_score": True,
    "repos_all_tests_passing": True,
    "repos_with_real_test_failures": False,
    "duplication_percentage": False,
    "cross_repo_identical_groups": False,
    "total_escapes": False,
    "escape_latency_median_days": False,
    "repos_with_e2e_suite": True,
    "repos_with_e2e_wired_into_ci": True,
}


def _get(out_dir: Path, filename: str, *path: str) -> float | None:
    p = out_dir / filename
    if not p.exists():
        return None
    try:
        data: object = read_json(p)
    except json.JSONDecodeError:
        return None
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data if isinstance(data, (int, float)) and not isinstance(data, bool) else None


def extract_metrics(out_dir: Path) -> dict[str, float | None]:
    return {
        "secrets_found": _get(out_dir, "security_summary.json", "total_secrets_found"),
        "semgrep_findings": _get(out_dir, "security_summary.json", "total_semgrep_findings"),
        "cve_findings": _get(out_dir, "deps_audit_summary.json", "total_cve_findings"),
        "outdated_packages": _get(out_dir, "deps_audit_summary.json", "total_outdated_packages"),
        "lint_errors": _get(out_dir, "lint_quality_summary.json", "total_errors"),
        "lint_warnings": _get(out_dir, "lint_quality_summary.json", "total_warnings"),
        "mean_mutation_score": _get(out_dir, "mutation_summary.json", "mean_mutation_score"),
        "repos_all_tests_passing": _get(out_dir, "testquality_summary.json", "repos_all_tests_passing"),
        "repos_with_real_test_failures": _get(
            out_dir, "testquality_summary.json", "repos_with_real_test_failures_right_now"),
        "duplication_percentage": _get(out_dir, "duplication_summary.json", "portfolio_stats", "percentage"),
        "cross_repo_identical_groups": _get(out_dir, "exact_duplicate_summary.json", "cross_repo_identical_groups"),
        "total_escapes": _get(out_dir, "escape_summary.json", "total_escapes_attributed"),
        "escape_latency_median_days": _get(out_dir, "escape_summary.json", "latency_days_median"),
        "repos_with_e2e_suite": _get(out_dir, "e2e_quality_summary.json", "repos_with_e2e_suite"),
        "repos_with_e2e_wired_into_ci": _get(out_dir, "e2e_quality_summary.json", "repos_with_e2e_wired_into_ci"),
    }


@dataclass
class TrendRow:
    metric: str
    baseline: float | None
    current: float | None
    delta: float | None
    direction: str  # "improved" / "regressed" / "unchanged" / "new" / "no_data"


def _classify(metric: str, baseline: float | None, current: float | None) -> TrendRow:
    if current is None:
        return TrendRow(metric, baseline, current, None, "no_data")
    if baseline is None:
        return TrendRow(metric, baseline, current, None, "new")
    delta = round(current - baseline, 4)
    if delta == 0:
        return TrendRow(metric, baseline, current, delta, "unchanged")
    higher_is_better = METRIC_DIRECTIONS.get(metric, True)
    improved = (delta > 0) == higher_is_better
    return TrendRow(metric, baseline, current, delta, "improved" if improved else "regressed")


def compare_to_baseline(out_dir: Path) -> list[TrendRow]:
    current = extract_metrics(out_dir)
    baseline_path = out_dir / BASELINE_FILENAME
    try:
        baseline = read_json(baseline_path) if baseline_path.exists() else {}
    except json.JSONDecodeError:
        baseline = {}
    if not isinstance(baseline, dict):
        baseline = {}
    return [_classify(metric, baseline.get(metric), value) for metric, value in current.items()]


def run_trends(out_dir: Path) -> Path:
    """Writes trend_report.json comparing this run against whatever
    baseline was saved here last time, THEN overwrites the baseline with
    this run's own metrics -- this run becomes the new "before" for
    whoever runs this again against the same --out directory."""
    rows = compare_to_baseline(out_dir)
    report_path = out_dir / "trend_report.json"
    write_json(report_path, {
        "metrics": [
            {"metric": r.metric, "baseline": r.baseline, "current": r.current,
             "delta": r.delta, "direction": r.direction}
            for r in rows
        ],
        "regressions": [r.metric for r in rows if r.direction == "regressed"],
        "improvements": [r.metric for r in rows if r.direction == "improved"],
    })
    write_json(out_dir / BASELINE_FILENAME, extract_metrics(out_dir))
    return report_path
