"""Composite per-repo risk ranking: combine every dimension's signal into one
ranked list, so "which repo needs attention first" has a documented, rerunnable
answer instead of being a gut call.

This is a ranking heuristic, not a ground truth -- said plainly rather than
implied away by decimal precision. Formula (each term min-max normalized to
[0,1] across the portfolio before weighting, 0 when a dimension has no data
for that repo):

  risk = 0.25 * escape_rate_norm
       + 0.20 * hotspot_norm      (sum of top-5 hotspot_score for that repo)
       + 0.15 * duplication_norm  (fraction of the repo's files that are
                                    exact cross-repo duplicates)
       + 0.15 * no_ci_gate        (1 if CI never runs tests, else 0)
       + 0.10 * test_failure_norm (tests_failed / tests_total, 0 if no tests ran)
       + 0.10 * security_norm     (secrets + semgrep findings attributed to repo)
       + 0.05 * bus_factor_norm   (top_author_share -- concentration risk)

Weights are a judgment call, stated so they can be argued with and changed;
they are not derived from the data.
"""
from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from ..core.util import write_csv, write_json

WEIGHTS = {
    "escape_rate": 0.25, "hotspot": 0.20, "duplication": 0.15, "no_ci_gate": 0.15,
    "test_failure": 0.10, "security": 0.10, "bus_factor": 0.05,
}


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _norm(values: Mapping[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {k: 0.0 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def run_synthesize(repo_names: list[str], out_dir: Path) -> Path:
    inventory = {r["repo"]: r for r in _read_csv(out_dir / "inventory.csv")}
    ci_gates = {r["repo"]: r for r in _read_csv(out_dir / "ci_gates.csv")}
    escapes = _read_csv(out_dir / "escapes.csv")
    hotspots = _read_csv(out_dir / "complexity_hotspots.csv")
    exact_dupes = _read_csv(out_dir / "exact_duplicate_files.csv")
    secrets = _read_csv(out_dir / "security_secrets.csv")
    semgrep = _read_csv(out_dir / "security_semgrep.csv")
    testruns = {r["repo"]: r for r in _read_csv(out_dir / "testquality_runs.csv")}

    escape_count: dict[str, int] = {r: 0 for r in repo_names}
    for e in escapes:
        escape_count[e["repo"]] = escape_count.get(e["repo"], 0) + 1

    hotspot_sum: dict[str, float] = {r: 0.0 for r in repo_names}
    by_repo_hotspots: dict[str, list[float]] = {}
    for h in hotspots:
        by_repo_hotspots.setdefault(h["repo"], []).append(float(h.get("hotspot_score", 0) or 0))
    for repo, scores in by_repo_hotspots.items():
        hotspot_sum[repo] = sum(sorted(scores, reverse=True)[:5])

    # Raw count of exact-duplicate-file groups this repo participates in
    # (not a fraction of its total files -- that denominator lives in
    # complexity_functions.csv per-repo file counts if a rate is needed later).
    dup_file_count: dict[str, int] = {r: 0 for r in repo_names}
    for g in exact_dupes:
        for repo in g.get("repos", "").split(";"):
            if repo:
                dup_file_count[repo] = dup_file_count.get(repo, 0) + 1

    no_ci_gate: dict[str, float] = {}
    for r in repo_names:
        gate = ci_gates.get(r, {})
        no_ci_gate[r] = 0.0 if gate.get("any_workflow_runs_tests") == "True" else 1.0

    test_failure: dict[str, float] = {}
    for r in repo_names:
        tr = testruns.get(r, {})
        total = int(tr.get("tests_total", 0) or 0)
        failed = int(tr.get("tests_failed", 0) or 0)
        test_failure[r] = (failed / total) if total > 0 else 0.0

    security_count: dict[str, int] = {r: 0 for r in repo_names}
    for s in secrets:
        security_count[s["repo"]] = security_count.get(s["repo"], 0) + 1
    for s in semgrep:
        security_count[s["repo"]] = security_count.get(s["repo"], 0) + 1

    bus_factor: dict[str, float] = {
        r: float(inventory.get(r, {}).get("top_author_share", 0) or 0) for r in repo_names
    }

    n_escape = _norm(escape_count)
    n_hotspot = _norm(hotspot_sum)
    n_dup = _norm(dup_file_count)
    n_security = _norm(security_count)

    rows = []
    for r in repo_names:
        score = (
            WEIGHTS["escape_rate"] * n_escape.get(r, 0)
            + WEIGHTS["hotspot"] * n_hotspot.get(r, 0)
            + WEIGHTS["duplication"] * n_dup.get(r, 0)
            + WEIGHTS["no_ci_gate"] * no_ci_gate.get(r, 0)
            + WEIGHTS["test_failure"] * test_failure.get(r, 0)
            + WEIGHTS["security"] * n_security.get(r, 0)
            + WEIGHTS["bus_factor"] * bus_factor.get(r, 0)
        )
        rows.append({
            "repo": r, "risk_score": round(score, 4),
            "escape_count": escape_count.get(r, 0),
            "top5_hotspot_sum": round(hotspot_sum.get(r, 0), 1),
            "exact_dup_file_count": dup_file_count.get(r, 0),
            "ci_gate_missing": bool(no_ci_gate.get(r, 0)),
            "test_failure_rate": round(test_failure.get(r, 0), 3),
            "security_findings": security_count.get(r, 0),
            "bus_factor_top_author_share": bus_factor.get(r, 0),
        })
    rows.sort(key=lambda r: -cast(float, r["risk_score"]))
    out_path = out_dir / "risk_ranking.csv"
    write_csv(out_path, rows)
    write_json(out_dir / "risk_weights.json", WEIGHTS)
    return out_path
