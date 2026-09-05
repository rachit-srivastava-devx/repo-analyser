"""Renders a REPORT.md from whatever module outputs exist in an analysis
output directory. Generic across any target this tool has been pointed at
-- reads what's there, says plainly what's missing, never invents a section
for data that wasn't produced.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from tabulate import tabulate


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _table(rows: list[dict], cols: list[str], limit: int | None = None) -> str:
    """GitHub-flavored markdown via `tabulate` (see deep_reports._md_table's
    docstring for why: not hand-rolled, and cells are pipe-escaped since
    neither this nor tabulate's own github format does that by default)."""
    if not rows:
        return "_(no data)_\n"
    rows = rows[:limit] if limit else rows
    safe_rows = [[str(r.get(c, "")).replace("|", "\\|") for c in cols] for r in rows]
    return tabulate(safe_rows, headers=cols, tablefmt="github") + "\n"


def render_report(out_dir: Path, target_name: str) -> Path:
    lines = [f"# Repo Analyser report: {target_name}", ""]
    run_log = _read_json(out_dir / "run_log.json")
    if run_log:
        lines.append(f"Repos analyzed: {run_log.get('repo_count', '?')}")
        ok = [m for m in run_log.get("modules_run", []) if m["status"] == "ok"]
        failed = [m for m in run_log.get("modules_run", []) if m["status"] == "error"]
        lines.append(f"Modules completed: {len(ok)}/{len(run_log.get('modules_run', []))}")
        if failed:
            lines.append(f"Modules that errored (see run_log.json): {[m['module'] for m in failed]}")
        lines.append("")

    inv = _read_csv(out_dir / "inventory.csv")
    if inv:
        lines += ["## Repo activity", "",
                   _table(inv, ["repo", "tier", "total_commits", "unique_authors",
                                "bus_factor_gini", "top_author_share"], limit=15),
                   f"_{len(inv)} repos total; showing top 15 by commit count._", ""]

    ci = _read_csv(out_dir / "ci_gates.csv")
    if ci:
        gated = sum(1 for r in ci if r.get("any_workflow_runs_tests") == "True")
        lines += ["## CI gates", "",
                   f"{gated}/{len(ci)} repos have a CI workflow that runs tests on any trigger.",
                   _table([r for r in ci if r.get("any_workflow_runs_tests") != "True"],
                          ["repo", "has_ci_config", "all_workflows_deploy_only"], limit=30), ""]

    ont = _read_json(out_dir / "ontology_summary.json")
    if ont:
        lines += ["## Commit ontology", "",
                   f"{ont.get('total_non_merge_commits', 0)} non-merge commits classified "
                   f"({ont.get('other_pct', 0)}% unclassified).", "",
                   "Superclass distribution (% of commits):", ""]
        for k, v in ont.get("superclass_pct", {}).items():
            lines.append(f"- {k}: {v}%")
        lines.append("")

    esc = _read_json(out_dir / "escape_summary.json")
    if esc:
        lines += ["## Defect escape (SZZ)", "",
                   f"{esc.get('total_escapes_attributed', 0)} bug-introducing commits attributed.",
                   f"Fix latency: median {esc.get('latency_days_median')}d, "
                   f"p90 {esc.get('latency_days_p90')}d.", ""]

    hotspots = _read_csv(out_dir / "complexity_hotspots.csv")
    if hotspots:
        lines += ["## Top hotspots (complexity x churn)", "",
                   _table(hotspots, ["repo", "file", "total_ccn", "n_revs", "hotspot_score"], limit=15), ""]

    dup_summary = _read_json(out_dir / "duplication_summary.json")
    exact_summary = _read_json(out_dir / "exact_duplicate_summary.json")
    if dup_summary or exact_summary:
        lines.append("## Duplication")
        lines.append("")
        if dup_summary:
            stats = dup_summary.get("portfolio_stats", {})
            lines.append(f"jscpd (block-level, >=10 lines): {stats.get('percentage', '?')}% duplicated lines, "
                         f"{dup_summary.get('cross_repo_clone_pairs', 0)} cross-repo clone pairs.")
        if exact_summary:
            lines.append(f"Exact (sha256, whole-file): {exact_summary.get('cross_repo_identical_same_path_groups', 0)} "
                         f"files are byte-identical across repos at the same path "
                         f"(max {exact_summary.get('max_repo_count_for_one_file', 0)} repos for one file).")
        lines.append("")

    sec = _read_json(out_dir / "security_summary.json")
    if sec:
        lines += ["## Security", "",
                   f"{sec.get('total_secrets_found', 0)} secrets found in git history "
                   f"(across {sec.get('repos_with_secrets', 0)} repos).",
                   f"{sec.get('total_semgrep_findings', 0)} semgrep findings: "
                   f"{sec.get('semgrep_by_severity', {})}", ""]

    tq = _read_json(out_dir / "testquality_summary.json")
    if tq:
        lines += ["## Test quality (real execution)", "",
                   f"{tq.get('repos_with_unit_script', 0)}/{tq.get('total_repos', 0)} repos have a runnable unit-test script.",
                   f"{tq.get('repos_with_real_test_failures_right_now', 0)} repos have failing tests RIGHT NOW.", ""]

    risk = _read_csv(out_dir / "risk_ranking.csv")
    if risk:
        lines += ["## Composite risk ranking", "",
                   _table(risk, ["repo", "risk_score", "escape_count", "top5_hotspot_sum",
                                "exact_dup_file_count", "ci_gate_missing", "security_findings"], limit=10), ""]

    report_path = out_dir / "REPORT.md"
    report_path.write_text("\n".join(lines))
    return report_path
