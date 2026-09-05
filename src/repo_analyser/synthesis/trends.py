"""Self-learning trend comparison: diff this run's key metrics against a
saved baseline from a prior run against the same --out directory, flagging
real regressions and improvements automatically -- rather than a human
eyeballing two runs side by side, which is what every before/after
comparison this tool has produced so far actually was (see
docs/METHODOLOGY.md #35).

Two baselines, tracked separately: portfolio-wide (extract_metrics,
trend_baseline.json -- unchanged since this module's original version) and
per-repo (extract_per_repo_metrics, trend_baseline_per_repo.json -- this
repo's own risk_score/mutation_score/etc. against ITS last run, not just
the portfolio mean, so "this one repo's mutation score dropped" surfaces
even when the portfolio average looks fine). Feeds per_repo_digest.py's
Trend section (ADR-0003) when a prior baseline exists.

Reads other collectors' already-written *_summary.json / *.csv files --
computes nothing new, matches this subpackage's own "no external tool
calls, reads every collector's output" rule (docs/ARCHITECTURE.md). A
curated, real subset of fields, not every field of every summary --
picked because each one answers "did this get healthier or worse," not
because it was the easiest field to grab.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ..core.util import read_json, write_json

BASELINE_FILENAME = "trend_baseline.json"
PER_REPO_BASELINE_FILENAME = "trend_baseline_per_repo.json"

# Per-repo metrics pulled straight from risk_ranking.csv (already computed
# there per repo) plus mutation_results.csv -- no new CSV reads beyond
# what synthesize.py/mutation.py already wrote. Same direction convention
# as METRIC_DIRECTIONS below.
PER_REPO_METRIC_DIRECTIONS: dict[str, bool] = {
    "risk_score": False,
    "escape_count": False,
    "top5_hotspot_sum": False,
    "exact_dup_file_count": False,
    "test_failure_rate": False,
    "security_findings": False,
    "mutation_score": True,
}

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


def _classify(metric: str, baseline: float | None, current: float | None,
              directions: dict[str, bool] = METRIC_DIRECTIONS) -> TrendRow:
    if current is None:
        return TrendRow(metric, baseline, current, None, "no_data")
    if baseline is None:
        return TrendRow(metric, baseline, current, None, "new")
    delta = round(current - baseline, 4)
    if delta == 0:
        return TrendRow(metric, baseline, current, delta, "unchanged")
    higher_is_better = directions.get(metric, True)
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


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_per_repo_metrics(out_dir: Path, repo_names: list[str]) -> dict[str, dict[str, float | None]]:
    """Per-repo counterpart to extract_metrics -- pulls from risk_ranking.csv
    (synthesize.py's per-repo scorecard, already computed) and
    mutation_results.csv, rather than re-deriving anything."""
    risk_by_repo = {r["repo"]: r for r in _read_csv(out_dir / "risk_ranking.csv")}
    mutation_by_repo = {r["repo"]: r for r in _read_csv(out_dir / "mutation_results.csv")}
    metrics: dict[str, dict[str, float | None]] = {}
    for name in repo_names:
        risk = risk_by_repo.get(name, {})
        mut = mutation_by_repo.get(name, {})
        metrics[name] = {
            "risk_score": _num(risk.get("risk_score")),
            "escape_count": _num(risk.get("escape_count")),
            "top5_hotspot_sum": _num(risk.get("top5_hotspot_sum")),
            "exact_dup_file_count": _num(risk.get("exact_dup_file_count")),
            "test_failure_rate": _num(risk.get("test_failure_rate")),
            "security_findings": _num(risk.get("security_findings")),
            "mutation_score": _num(mut.get("mutation_score")) if mut.get("ran") == "True" else None,
        }
    return metrics


def compare_per_repo_to_baseline(out_dir: Path, repo_names: list[str]) -> dict[str, list[TrendRow]]:
    current = extract_per_repo_metrics(out_dir, repo_names)
    baseline_path = out_dir / PER_REPO_BASELINE_FILENAME
    try:
        baseline_all = read_json(baseline_path) if baseline_path.exists() else {}
    except json.JSONDecodeError:
        baseline_all = {}
    if not isinstance(baseline_all, dict):
        baseline_all = {}
    return {
        name: [_classify(metric, baseline_all.get(name, {}).get(metric), value, PER_REPO_METRIC_DIRECTIONS)
               for metric, value in current[name].items()]
        for name in repo_names
    }


def run_trends(out_dir: Path, repo_names: list[str] | None = None) -> Path:
    """Writes trend_report.json comparing this run against whatever
    baseline was saved here last time, THEN overwrites the baseline with
    this run's own metrics -- this run becomes the new "before" for
    whoever runs this again against the same --out directory.

    repo_names is optional (None keeps the old portfolio-only behavior)
    so a caller on an older workflow that hasn't updated its call site yet
    still gets the portfolio-wide report -- just not the per-repo one."""
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

    if repo_names:
        per_repo_rows = compare_per_repo_to_baseline(out_dir, repo_names)
        write_json(out_dir / "trend_report_per_repo.json", {
            name: {
                "regressions": [r.metric for r in rows_ if r.direction == "regressed"],
                "improvements": [r.metric for r in rows_ if r.direction == "improved"],
                "metrics": [{"metric": r.metric, "baseline": r.baseline, "current": r.current,
                             "delta": r.delta, "direction": r.direction} for r in rows_],
            }
            for name, rows_ in per_repo_rows.items()
        })
        write_json(out_dir / PER_REPO_BASELINE_FILENAME, extract_per_repo_metrics(out_dir, repo_names))
    return report_path
