"""Generates one capstone executive deck spec spanning every category --
matching the reference engagement's "Slide N / Purpose / Content / Visual /
Takeaway" blueprint format exactly. This is a script for a human (or a
slide-design pass) to render into actual slides -- it is not itself a
rendered deck.

Every number pulled in is read from that run's own JSON/CSV summaries;
nothing here is specific to any one target.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

Row = dict


def _read_csv(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _fnum(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _slide(n: int, title: str, purpose: str, content: list[str], visual: str, takeaway: str) -> str:
    bullets = "\n".join(f"  - {c}" for c in content)
    return f"""### Slide {n} — {title}
- **Purpose:** {purpose}
- **Content:**
{bullets}
- **Visual:** {visual}
- **Takeaway:** {takeaway}
"""


def generate_deck(data_dir: Path, target_name: str) -> str:
    inv = _read_csv(data_dir / "inventory.csv")
    ont = _read_json(data_dir / "ontology_summary.json")
    escape = _read_json(data_dir / "escape_summary.json")
    escape_monthly = _read_csv(data_dir / "escape_monthly.csv")
    dup = _read_json(data_dir / "duplication_summary.json")
    exact_dup = _read_json(data_dir / "exact_duplicate_summary.json")
    ci = _read_csv(data_dir / "ci_gates.csv")
    security = _read_json(data_dir / "security_summary.json")
    testq = _read_json(data_dir / "testquality_summary.json")
    effort = _read_json(data_dir / "effort_summary.json")
    risk = _read_csv(data_dir / "risk_ranking.csv")

    n_repos = len(inv)
    total_commits = sum(int(r["total_commits"]) for r in inv) if inv else 0
    gated = sum(1 for r in ci if r.get("any_workflow_runs_tests") == "True")
    ungated = len(ci) - gated

    rates = [_fnum(r["escape_rate_12mo"]) * 100 for r in escape_monthly]
    recent_rate = f"{min(rates[-4:]):.0f}-{max(rates[-4:]):.0f}%" if len(rates) >= 4 else "n/a"

    top_risk = sorted(risk, key=lambda r: -_fnum(r["risk_score"]))[:3] if risk else []
    top_risk_names = ", ".join(r["repo"] for r in top_risk)

    slides = []
    slides.append(_slide(
        1, "Cover / why this engagement happened",
        "Frame the whole briefing before any data.",
        [f"This is one integrated analysis of {target_name}'s engineering estate: {n_repos} repos, "
         f"{total_commits} commits, ten measurement categories, cross-referenced against each other.",
         "The question: where is real risk actually concentrated, and what is the highest-leverage fix?",
         "Every number in this deck traces to a CSV/JSON that ships alongside it -- nothing here is "
         "asserted without a rerunnable source."],
        "none -- title/framing slide.",
        "One integrated analysis, ten categories, one prioritized action list.",
    ))
    slides.append(_slide(
        2, f"The estate at a glance: {n_repos} repos",
        "Establish the structural starting point.",
        [f"{n_repos} repos analyzed, {total_commits} total commits.",
         f"CI gate status: **{gated} of {len(ci)}** repos actually run tests before merge/deploy; "
         f"**{ungated}** configure CI for build/deploy only.",
         f"Duplication: {exact_dup.get('cross_repo_identical_same_path_groups', 0) if exact_dup else 0} "
         f"files are byte-identical across multiple repos." if exact_dup else "Single-repo target -- cross-repo duplication does not apply."],
        "charts/repo_activity_top15.png",
        f"{ungated} of {len(ci)} repos ship without a test gate." if ungated else "CI gating is in good shape across this portfolio.",
    ))
    slides.append(_slide(
        3, "Where the time goes",
        "Establish the effort baseline.",
        [f"Delivery (new capability) is **{ont.get('superclass_pct', {}).get('delivery', '?')}%** of all "
         f"classified commits; Correction (bug fixes + reverts) is "
         f"**{ont.get('superclass_pct', {}).get('correction', '?')}%**.",
         f"{effort.get('toil_clusters_found', 0)} candidate toil clusters found, covering "
         f"{effort.get('toil_commits_in_clusters', 0)} commits of repeated, mechanical work."] if ont else ["No ontology data available."],
        "charts/effort_share_over_time.png",
        "See EFFORT_ALLOCATION.md for the full per-author and per-cluster breakdown.",
    ))
    slides.append(_slide(
        4, "Defect escape rate",
        "State the quality-risk trend plainly.",
        [f"{escape.get('total_escapes_attributed', 0)} bug-introducing commits attributed (SZZ). "
         f"Median fix latency {escape.get('latency_days_median', '?')} days, p90 "
         f"{escape.get('latency_days_p90', '?')} days.",
         f"Most recent observed months: {recent_rate} escape rate."] if escape else ["No escape data available."],
        "charts/escape_trend.png",
        "See ESCAPE.md for the full monthly series and per-repo breakdown.",
    ))
    slides.append(_slide(
        5, "Security",
        "Name what needs action today, separate from everything else.",
        [f"{security.get('total_secrets_found', 0)} secret-history findings across "
         f"{security.get('repos_with_secrets', 0)} repos (gitleaks, full git history).",
         f"{security.get('total_semgrep_findings', 0)} code-pattern findings (semgrep)."] if security else ["No security data available."],
        "none -- see SECURITY.md for the per-repo, per-rule breakdown.",
        "Credential rotation, where applicable, is a today action independent of the rest of this deck.",
    ))
    slides.append(_slide(
        6, "Test quality: real execution, not a proxy",
        "Distinguish 'has tests' from 'tests pass, right now.'",
        [f"{testq.get('repos_all_tests_passing', 0)} repos fully passing right now.",
         f"{testq.get('repos_with_real_test_failures_right_now', 0)} repos have real failures right now.",
         f"{testq.get('repos_with_test_infra_but_zero_tests_written', 0)} repos have a working harness and "
         f"zero tests behind it."] if testq else ["No test-quality data available."],
        "none.",
        "Every number in this section came from actually running the suite, not counting test files.",
    ))
    slides.append(_slide(
        7, "The highest-priority repos",
        "Turn everything above into a short, specific list.",
        [f"By composite risk score (escape rate, hotspots, duplication, missing CI gates, test "
         f"failures, security findings, bus-factor): {top_risk_names or 'see risk_ranking.csv'}."],
        "none -- see CONSOLIDATION_ROADMAP.md's ranked table.",
        f"{top_risk_names or 'The full ranked list'} carries the most compounding risk right now.",
    ))
    slides.append(_slide(
        8, "The ask",
        "State the concrete next step.",
        ["See CONSOLIDATION_ROADMAP.md section 2 for the full, numbered action list, ordered by "
         "leverage and urgency.",
         "This deck and every underlying number can be regenerated at any time by re-running "
         "`python3 cli.py analyze` against the same target."],
        "none.",
        "The data, the ranking, and the action list are all reproducible -- rerun this analysis "
        "on a cadence to track whether the picture is improving.",
    ))

    return f"""# {target_name} — *Capstone* Briefing (deck spec)

**Deck meta:** Audience: engineering leadership. Slide count: {len(slides)}. Generated from this
run's own data -- every number below traces to a CSV/JSON in this output directory. This is a
*specification* for a deck, not a rendered one: hand it to a slide-design pass (or read it
directly) to produce the actual presentation.

---

{"".join(slides)}
"""


def run_exec_deck(data_dir: Path, target_name: str) -> Path:
    content = generate_deck(data_dir, target_name)
    out_path = data_dir / "CAPSTONE_DECK.md"
    out_path.write_text(content)
    return out_path
