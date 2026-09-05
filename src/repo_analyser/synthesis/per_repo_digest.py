"""Per-repo digest: one consolidated markdown page per repo in the target,
pulling that repo's own rows out of every collector's CSV/JSON -- the
per-repo counterpart to deep_reports.py's portfolio-wide reports.

See docs/adr/0003-per-repo-digest-reports.md for why this exists as an
addition (not a replacement) and why it's scoped to one consolidated page
per repo rather than one file per category per repo. Every number below is
computed fresh from that run's own CSV/JSON, same rule deep_reports.py
follows -- nothing hardcoded from a specific run.
"""
from __future__ import annotations

import csv
from pathlib import Path

from tabulate import tabulate

Row = dict


def _read_csv(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _fnum(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    safe_rows = [[str(c).replace("|", "\\|") for c in r] for r in rows]
    return tabulate(safe_rows, headers=headers, tablefmt="github")


def _for_repo(rows: list[Row], repo_name: str, key: str = "repo") -> list[Row]:
    return [r for r in rows if r.get(key) == repo_name]


class _AllData:
    """Every CSV/JSON this module reads, loaded once per run (not once per
    repo) -- a 180-repo portfolio (chronicle_button scale) would otherwise
    re-read every file 180 times for no reason."""

    def __init__(self, data_dir: Path) -> None:
        self.inventory = _read_csv(data_dir / "inventory.csv")
        self.ci_gates = _read_csv(data_dir / "ci_gates.csv")
        self.risk_ranking = _read_csv(data_dir / "risk_ranking.csv")
        self.hotspots = _read_csv(data_dir / "complexity_hotspots.csv")
        self.lint = _read_csv(data_dir / "lint_quality.csv")
        self.code_quality = _read_csv(data_dir / "code_quality.csv")
        self.testquality = _read_csv(data_dir / "testquality_runs.csv")
        self.mutation = _read_csv(data_dir / "mutation_results.csv")
        self.secrets = _read_csv(data_dir / "security_secrets.csv")
        self.semgrep = _read_csv(data_dir / "security_semgrep.csv")
        self.duplication_clones = _read_csv(data_dir / "duplication_clones.csv")
        self.exact_duplicates = _read_csv(data_dir / "exact_duplicate_files.csv")
        self.escapes = _read_csv(data_dir / "escapes.csv")
        self.deps_cves = _read_csv(data_dir / "deps_cves.csv")
        # Performance/latency budget: no collector writes this yet (see
        # docs/ROADMAP.md) -- absence is reported explicitly below, never
        # silently skipped, per ADR-0001.
        self.performance = _read_csv(data_dir / "performance_summary.csv")


def _section_header(repo_name: str, data: _AllData, target_name: str) -> str:
    inv = _for_repo(data.inventory, repo_name)
    tier = inv[0]["tier"] if inv else "unknown"
    ranking_sorted = sorted(data.risk_ranking, key=lambda r: -_fnum(r.get("risk_score")))
    rank_line = "_Not ranked -- `synthesize` has not run for this target yet._"
    for i, r in enumerate(ranking_sorted, start=1):
        if r.get("repo") == repo_name:
            rank_line = (f"Ranked **#{i} of {len(ranking_sorted)}** by composite risk score "
                         f"(`{_fnum(r.get('risk_score')):.3f}`).")
            break
    return (f"# {repo_name} — Repo Digest\n\n"
            f"_Part of the `{target_name}` target. {rank_line} See `RISK_RANKING.csv`/"
            f"`CONSOLIDATION_ROADMAP.md` in the portfolio-wide reports for how this repo compares "
            f"to the rest of `{target_name}`._\n\n"
            f"**Activity tier:** {tier}\n")


def _section_ci_gate(repo_name: str, data: _AllData) -> str:
    rows = _for_repo(data.ci_gates, repo_name)
    if not rows:
        return "## CI gate\n\n_No `ci_gates.csv` row for this repo -- run the `ci_gates` module._\n"
    r = rows[0]
    if r.get("has_ci_config") != "True":
        return "## CI gate\n\n**No CI configuration found.** Nothing blocks a bad merge.\n"
    gated = r.get("any_workflow_runs_tests") == "True"
    verdict = "**Gated:** at least one workflow runs tests." if gated else \
        "**Not gated:** CI exists but no workflow runs tests (deploy-only)."
    return (f"## CI gate\n\n{verdict} {r.get('workflow_count', '0')} workflow file(s): "
            f"`{r.get('workflow_files', '')}`.\n")


def _section_coding(repo_name: str, data: _AllData) -> str:
    hotspots = sorted(_for_repo(data.hotspots, repo_name), key=lambda r: -_fnum(r.get("hotspot_score")))[:5]
    out = ["## Coding quality\n"]
    if hotspots:
        out.append("**Top complexity×churn hotspots:**\n")
        out.append(_md_table(
            ["File", "Hotspot score", "Max CCN", "Revisions"],
            [[h["file"], f"{_fnum(h.get('hotspot_score')):.1f}", h.get("max_ccn", "?"), h.get("n_revs", "?")]
             for h in hotspots]))
        out.append("")
    else:
        out.append("_No complexity hotspots recorded for this repo._\n")
    lint_rows = _for_repo(data.lint, repo_name)
    if lint_rows and lint_rows[0].get("ran") == "True":
        lr = lint_rows[0]
        out.append(f"**Lint ({lr.get('linter', '?')}):** {lr.get('error_count', '0')} errors, "
                    f"{lr.get('warning_count', '0')} warnings across {lr.get('files_with_issues', '0')} file(s).\n")
    elif lint_rows and lint_rows[0].get("skip_reason"):
        out.append(f"**Lint:** skipped -- {lint_rows[0]['skip_reason']}\n")
    cq_rows = _for_repo(data.code_quality, repo_name)
    if cq_rows and cq_rows[0].get("ran") == "True":
        cq = cq_rows[0]
        out.append(f"**Maintainability index (radon):** mean {_fnum(cq.get('mean_maintainability_index')):.1f} "
                    f"(grade {cq.get('grade', '?')}); lowest: `{cq.get('lowest_file', '?')}` "
                    f"({_fnum(cq.get('lowest_file_mi')):.1f}).\n")
    return "\n".join(out)


def _section_testing_mutation(repo_name: str, data: _AllData) -> str:
    out = ["## Testing & mutation\n"]
    tq_rows = _for_repo(data.testquality, repo_name)
    if tq_rows and tq_rows[0].get("ran") == "True":
        tq = tq_rows[0]
        passed, failed = _fnum(tq.get("tests_passed")), _fnum(tq.get("tests_failed"))
        out.append(f"**Test suite ({tq.get('runner_detected', '?')}):** {int(passed)} passed, "
                    f"{int(failed)} failed of {tq.get('tests_total', '?')} in {tq.get('duration_s', '?')}s.\n")
    elif tq_rows and tq_rows[0].get("skip_reason"):
        out.append(f"**Test suite:** skipped -- {tq_rows[0]['skip_reason']}\n")
    else:
        out.append("_No test-quality data for this repo._\n")
    mut_rows = _for_repo(data.mutation, repo_name)
    if mut_rows and mut_rows[0].get("ran") == "True":
        m = mut_rows[0]
        out.append(f"**Mutation score:** {_fnum(m.get('mutation_score')):.1%} on `{m.get('file_mutated', '?')}` "
                    f"({m.get('killed', '0')} killed / {m.get('survived', '0')} survived / "
                    f"{m.get('no_coverage', '0')} no-coverage of {m.get('total_mutants', '0')}).\n")
    elif mut_rows and mut_rows[0].get("skip_reason"):
        out.append(f"**Mutation testing:** skipped -- {mut_rows[0]['skip_reason']}\n")
    else:
        out.append("_No mutation-testing data for this repo (not selected as a target this run)._\n")
    return "\n".join(out)


def _section_security(repo_name: str, data: _AllData) -> str:
    secrets = _for_repo(data.secrets, repo_name)
    semgrep = _for_repo(data.semgrep, repo_name)
    out = ["## Security\n"]
    if secrets:
        out.append(f"**{len(secrets)} committed secret(s) found** (gitleaks, full git history):\n")
        out.append(_md_table(["Rule", "File", "Date"],
                              [[s.get("rule_id", "?"), s.get("file", "?"), s.get("date", "?")] for s in secrets[:10]]))
        out.append("")
    else:
        out.append("No committed secrets found (gitleaks).\n")
    if semgrep:
        out.append(f"**{len(semgrep)} semgrep finding(s):**\n")
        out.append(_md_table(["Severity", "Rule", "File:line"],
                              [[s.get("severity", "?"), s.get("check_id", "?"),
                                f"{s.get('file', '?')}:{s.get('start_line', '?')}"] for s in semgrep[:10]]))
        out.append("")
    else:
        out.append("No semgrep findings.\n")
    return "\n".join(out)


def _section_performance(repo_name: str, data: _AllData) -> str:
    rows = _for_repo(data.performance, repo_name)
    if not rows:
        return ("## Performance / latency budget\n\n"
                "_Not yet measured -- no `performance` module has run for this target. "
                "See `docs/ROADMAP.md` for the planned collector (benchmark execution + "
                "budget-config detection). This is stated explicitly rather than omitted, "
                "per ADR-0001's fail-loud-not-silent rule._\n")
    r = rows[0]
    return f"## Performance / latency budget\n\n{r}\n"  # shape TBD when the collector lands


def _section_duplication_involvement(repo_name: str, data: _AllData) -> str:
    clone_rows = [r for r in data.duplication_clones
                  if r.get("repo_a") == repo_name or r.get("repo_b") == repo_name]
    cross_repo_partners = sorted({(r["repo_b"] if r["repo_a"] == repo_name else r["repo_a"])
                                   for r in clone_rows if r.get("is_cross_repo") == "True"})
    exact_groups = [r for r in data.exact_duplicates
                    if repo_name in (r.get("repos", "").split(";"))]
    out = ["## Duplication involvement\n"]
    if cross_repo_partners:
        out.append(f"Shares cloned code blocks with **{len(cross_repo_partners)} other repo(s)**: "
                    f"{', '.join(cross_repo_partners[:10])}"
                    f"{'...' if len(cross_repo_partners) > 10 else ''}. "
                    f"Candidate signal for extracting a shared library (see `CONSOLIDATION_ROADMAP.md`).\n")
    else:
        out.append("No cross-repo block-level clones involving this repo.\n")
    if exact_groups:
        out.append(f"Party to **{len(exact_groups)} byte-identical file group(s)** shared with other repos.\n")
    else:
        out.append("No byte-identical files shared with other repos.\n")
    return "\n".join(out)


def _section_escape_and_deps(repo_name: str, data: _AllData) -> str:
    esc = _for_repo(data.escapes, repo_name)
    cves = _for_repo(data.deps_cves, repo_name)
    out = ["## Defect escape & dependencies\n"]
    if esc:
        latencies = [_fnum(r.get("latency_days")) for r in esc]
        out.append(f"**{len(esc)} defect(s)** escaped to production; latency to fix ranged "
                    f"{min(latencies):.0f}-{max(latencies):.0f} days "
                    f"(mean {sum(latencies) / len(latencies):.0f}).\n")
    else:
        out.append("No defect escapes recorded (SZZ).\n")
    if cves:
        by_sev: dict[str, int] = {}
        for c in cves:
            by_sev[c.get("severity", "unknown")] = by_sev.get(c.get("severity", "unknown"), 0) + 1
        out.append(f"**{len(cves)} known-CVE dependency issue(s)**: " +
                    ", ".join(f"{n} {sev}" for sev, n in sorted(by_sev.items())) + ".\n")
    else:
        out.append("No known-CVE dependency issues found (osv-scanner).\n")
    return "\n".join(out)


def render_repo_digest(repo_name: str, data: _AllData, target_name: str) -> str:
    sections = [
        _section_header(repo_name, data, target_name),
        _section_ci_gate(repo_name, data),
        _section_coding(repo_name, data),
        _section_testing_mutation(repo_name, data),
        _section_security(repo_name, data),
        _section_performance(repo_name, data),
        _section_duplication_involvement(repo_name, data),
        _section_escape_and_deps(repo_name, data),
        "## Honest limitations\n\n"
        "This page is a consolidated digest, not a full re-statement of every category -- "
        "effort/ownership mix, the full dependency graph, and E2E/supply-chain detail live only "
        "in the portfolio-wide reports (`deep_reports.py`'s `EFFORT_ALLOCATION.md`/`DEPGRAPH.md`/"
        "etc.), not duplicated here. Cross-repo relationships (this section's \"shares cloned code "
        "with\") are listed by name only; the full pairwise detail is in `duplication_clones.csv`.\n",
    ]
    return "\n".join(sections)


def run_per_repo_digest(data_dir: Path, out_dir: Path, repo_names: list[str], target_name: str) -> list[Path]:
    """Writes one digest per repo in repo_names, plus an index. Returns the
    list of paths written (index first, then one per repo, in repo_names'
    order -- callers that care about a stable order should pass repo_names
    pre-sorted, matching how discover_repos already returns a sorted list)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _AllData(data_dir)
    written = []
    index_rows = []
    for repo_name in repo_names:
        digest = render_repo_digest(repo_name, data, target_name)
        path = out_dir / f"{repo_name}.md"
        path.write_text(digest)
        written.append(path)
        tier_rows = _for_repo(data.inventory, repo_name)
        index_rows.append([repo_name, tier_rows[0]["tier"] if tier_rows else "?",
                            f"[{repo_name}.md]({repo_name}.md)"])
    index = (f"# {target_name} — Per-repo digest index\n\n"
             f"One consolidated page per repo. For ecosystem-wide views (cross-repo duplication, "
             f"shared dependencies, risk ranking), see the portfolio-wide reports one level up.\n\n"
             + (_md_table(["Repo", "Tier", "Digest"], index_rows) if index_rows
                else "_No repos in this target._\n"))
    index_path = out_dir / "PER_REPO_INDEX.md"
    index_path.write_text(index)
    return [index_path] + written
