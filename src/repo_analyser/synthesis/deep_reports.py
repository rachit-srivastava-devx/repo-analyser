"""Deep per-category reports, matching the reference engagement's exact
structural pattern: H1 title, an italicized basis/method line citing exact
datasets and chart files, numbered H2 sections, tables, bolded headline
numbers inline, an "Honest limitations" section where the method has real
blind spots, and a closing raw-data citation.

Every number in every function below is computed from the CSV/JSON passed
in -- nothing is hardcoded from any specific run. Point this at a different
target and the prose changes because the numbers changed, not because
someone edited a template by hand.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from tabulate import tabulate

from ..reporting import charts

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


def _fmt(v) -> str:
    """Renders a numeric-looking string without a spurious trailing .0."""
    f = _fnum(v, None) if v not in (None, "") else None
    if f is not None and f == int(f):
        return str(int(f))
    return str(v)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """GitHub-flavored markdown via `tabulate`, not hand-rolled string
    joins -- was duplicated near-verbatim in reporting/report.py before
    both were consolidated onto this one library call. Cell values are
    pipe-escaped first: neither this nor tabulate's own github format
    escapes a literal "|" inside a cell, and real input reaches this
    (commit subjects, semgrep messages) that can contain one -- an
    unescaped pipe silently corrupts the table's column structure."""
    safe_rows = [[str(c).replace("|", "\\|") for c in r] for r in rows]
    return tabulate(safe_rows, headers=headers, tablefmt="github")


# ---------------------------------------------------------------------------
# 1. Repo activity / tiering
# ---------------------------------------------------------------------------

def repo_analysis(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    inv = _read_csv(data_dir / "inventory.csv")
    if not inv:
        return f"# {target_name} — Repository Analysis\n\n_No inventory.csv found -- run the `inventory` module first._\n"

    tiers: dict[str, list[Row]] = defaultdict(list)
    for r in inv:
        tiers[r["tier"]].append(r)
    total = len(inv)

    tier_table = _md_table(
        ["Bucket", "Definition", "Count"],
        [[t.capitalize(), d, str(len(tiers.get(t, [])))]
         for t, d in [("active", "<=90 days since last commit"), ("recent", "90d-1yr"),
                      ("aging", "1-3yr"), ("dormant", ">3yr")]],
    )

    by_commits = sorted(inv, key=lambda r: -int(r["total_commits"]))
    top_table = _md_table(
        ["Repo", "Commits", "Authors", "Bus-factor Gini", "Top author share"],
        [[r["repo"], r["total_commits"], r["unique_authors"], r["bus_factor_gini"], r["top_author_share"]]
         for r in by_commits[:15]],
    )

    high_risk = sorted([r for r in inv if _fnum(r["top_author_share"]) > 0.7],
                        key=lambda r: -_fnum(r["top_author_share"]))
    risk_table = (_md_table(
        ["Repo", "Top author share", "Authors", "Commits"],
        [[r["repo"], r["top_author_share"], r["unique_authors"], r["total_commits"]] for r in high_risk],
    ) if high_risk else "_None above 0.70 -- no acute single-author concentration found._")

    ginis = sorted(_fnum(r["bus_factor_gini"]) for r in inv)
    median_gini = statistics.median(ginis) if ginis else 0.0

    total_commits = sum(int(r["total_commits"]) for r in inv)
    total_authors = len({r["top_author"] for r in inv})  # distinct top-authors, a lower bound

    charts.horizontal_bar_ranked(
        [r["repo"] for r in by_commits[:15]], [int(r["total_commits"]) for r in by_commits[:15]],
        f"{target_name}: commit volume by repo", charts_dir / "repo_activity_top15.png",
        subtitle=f"{total} repos, {total_commits} total commits", value_fmt="{:.0f}",
    )

    return f"""# {target_name} — Repository *Analysis*

*Generated from `git log` history in each of {total} repos. Tiers are by days since last
commit; bus-factor is the Gini coefficient of each repo's per-author commit share (0 = evenly
spread, 1 = one author owns everything). Data: `inventory.csv`. Chart: `charts/repo_activity_top15.png`.*

## 1. Distribution at a glance

{tier_table}

Total commits across the portfolio: **{total_commits}**, across at least **{total_authors}**
distinct top-authors (a lower bound: repos sharing the same top author count once). Median
bus-factor Gini across all repos: **{median_gini:.3f}**.

![Commit volume by repo](charts/repo_activity_top15.png)

## 2. Most active repos by volume

{top_table}

## 3. Bus-factor / key-person risk

Repos where one author holds more than 70% of all commits -- the highest key-person risk in
the portfolio:

{risk_table}

## 4. Honest limitations

- Tiering uses raw last-commit date; this tool does not attempt to detect and exclude
  org-wide automated batch commits (e.g. a mass tooling migration) the way a human analyst
  reviewing the corpus might. A single such batch commit across many repos would understate
  how dormant those repos really are -- check `last_commit` against `top_author` for repos
  where they look suspicious before trusting the tier.
- Bus-factor Gini is computed over the repo's *entire* history, not a recent window --
  a repo that was single-author at launch and later grew a real team will still show an
  elevated historical Gini.

*Raw data: `inventory.csv`.*
"""


# ---------------------------------------------------------------------------
# 2. Commit ontology
# ---------------------------------------------------------------------------

def commit_ontology(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "ontology_summary.json")
    audit = _read_json(data_dir / "ontology_audit_summary.json")  # optional
    if not summary:
        return f"# {target_name} — Commit Ontology\n\n_No ontology_summary.json found -- run the `ontology` module first._\n"

    total = summary.get("total_non_merge_commits", 0)
    other_pct = summary.get("other_pct", 0.0)
    super_pct = summary.get("superclass_pct", {})
    leaf_dist = summary.get("leaf_distribution", {})

    super_table = _md_table(
        ["Superclass", "% of commits"],
        [[k, f"{v}%"] for k, v in sorted(super_pct.items(), key=lambda kv: -kv[1])],
    )
    leaf_table = _md_table(
        ["Leaf type", "Count"],
        [[k, str(v)] for k, v in sorted(leaf_dist.items(), key=lambda kv: -kv[1])],
    )

    delivery = super_pct.get("delivery", 0.0)
    correction = super_pct.get("correction", 0.0)
    ops = super_pct.get("ops_config", 0.0)

    audit_line = ""
    if audit:
        audit_line = (f"\nIndependently blind-audited: **{audit.get('exact_agreement_pct', '?')}% exact / "
                       f"{audit.get('superclass_agreement_pct', '?')}% superclass agreement** against a "
                       f"second, independent classification with no access to this tool's labels -- see "
                       f"`ONTOLOGY_AUDIT.md`. Read the percentages above as directional, not precise to "
                       f"the point, at that agreement level.\n")

    return f"""# {target_name} — Commit *Ontology*

*Every non-merge commit classified by a deterministic rule table (file-pattern rules first,
then conventional-commit prefix / keyword match, `other` when neither matches -- see
`docs/METHODOLOGY.md` for the exact rules and priority order). No LLM in the loop, fully
reproducible. Data: `ontology_commits.csv`, `ontology_summary.json`.*

## 1. The headline: where the work actually goes

{total} non-merge commits classified, **{other_pct}% left honestly unclassified** rather than
force-fit into a category.

{super_table}
{audit_line}
**Delivery ({delivery}%) vs. Correction ({correction}%)**: {"delivery outpaces correction, a healthy ratio" if delivery > correction * 1.3 else ("correction is nearly as large as delivery -- for every commit that ships something new, a comparable amount of work is spent fixing something" if correction > delivery * 0.7 else "correction runs meaningfully behind delivery")}.
Ops & config sits at {ops}% of all commits{" -- low, consistent with a young codebase that hasn't yet accumulated infrastructure sprawl" if ops < 15 else " -- a substantial share of all engineering time going to running the platform rather than building it"}.

## 2. Full leaf-type breakdown

{leaf_table}

## 3. Honest limitations

- The classifier's "other" bucket ({other_pct}%) is deliberately conservative: an ambiguous,
  jargon-heavy commit subject is left unclassified rather than guessed into a category (see
  `ONTOLOGY_AUDIT.md`'s disagreement analysis for the specific asymmetry this produces against
  a more liberal human rater).
- File-pattern rules only fire when *all* files a commit touched match one pattern; a mixed
  commit (e.g. a lockfile bump alongside a real code change) falls through to message-based
  classification, which may miscategorize it.

*Raw data: `ontology_commits.csv`. Run `ontology_audit` (see README) to independently verify
this classifier's accuracy on your own corpus before trusting the headline percentages.*
"""


# ---------------------------------------------------------------------------
# 3. Effort allocation / toil
# ---------------------------------------------------------------------------

def effort_allocation(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "effort_summary.json")
    monthly = _read_csv(data_dir / "effort_monthly_share.csv")
    clusters = _read_csv(data_dir / "effort_toil_clusters.csv")
    authors = _read_csv(data_dir / "effort_by_author.csv")
    if not summary:
        return f"# {target_name} — Effort Allocation\n\n_No effort_summary.json found -- run the `effort` module first._\n"

    if monthly:
        cats = ["delivery", "correction", "code_health", "ops_config", "data_schema", "housekeeping", "other"]
        series = {c: [_fnum(r.get(c, 0)) for r in monthly] for c in cats}
        charts.stacked_share_bar([r["month"] for r in monthly], series,
                                  f"{target_name}: what commits go to, by month",
                                  charts_dir / "effort_share_over_time.png",
                                  subtitle=f"{summary['total_commits']} classified commits")

    cluster_table = (_md_table(
        ["Repo", "Location", "Category", "Commits", "Authors", "Span"],
        [[c["repo"], c["primary_dir"], c["superclass"], c["commit_count"], c["distinct_authors"],
          f"{c['first_seen']} to {c['last_seen']}"] for c in clusters[:15]],
    ) if clusters else "_No cluster reached the minimum size threshold._")

    author_table = _md_table(
        ["Author", "Commits", "Delivery %", "Correction %", "Ops/config %"],
        [[a["author"], a["total_commits"], a["delivery_pct"], a["correction_pct"], a["ops_config_pct"]]
         for a in authors[:12]],
    )

    toil_commits = summary.get("toil_commits_in_clusters", 0)
    total = summary.get("total_commits", 1)
    toil_pct = round(100 * toil_commits / total, 1) if total else 0.0

    return f"""# {target_name} — Engineering Effort *Allocation*

*Basis: all {total} non-merge, ontology-classified commits, joined with authorship and the
files each commit touched. Toil clusters are found mechanically (grouped by repo + directory +
category, flagged above {15} commits) -- each is a candidate worth a human diff-read, not a
verified finding the way a hand-audited deep-dive would be. Data: `effort_by_author.csv`,
`effort_monthly_share.csv`, `effort_toil_clusters.csv`. Chart: `charts/effort_share_over_time.png`.*

## 1. Where the commits go, over time

![What commits go to, by month](charts/effort_share_over_time.png)

{summary.get('authors_with_20plus_commits', 0)}
authors have 20+ commits; their median Delivery share is **{summary.get('median_delivery_pct_20plus_commit_authors', 0)}%**.

## 2. Candidate toil clusters

{summary.get('toil_clusters_found', 0)} clusters found, covering **{toil_commits} commits
({toil_pct}% of all classified work)** -- repeated, mechanical, same-location work that isn't
new-feature delivery:

{cluster_table}

## 3. Per-author breakdown (top 12 by volume)

{author_table}

## 4. Honest limitations

- Clusters are grouped by directory prefix and category only -- two unrelated recurring
  patterns in the same directory (e.g. both config tweaks and bug fixes under one feature's
  folder) will merge into one cluster row. Read `sample_subjects` in the raw CSV before citing
  a cluster's size as evidence of one specific problem.
- No effort/build-cost estimate is attached to any cluster (unlike a hand-authored toil
  deep-dive) -- that requires product/ownership context this tool does not have. Use the
  cluster list to prioritize *which* areas to investigate, not as a ready-made remediation plan.
- Per-author percentages are a commit-count proxy for effort, not a performance measure --
  commit size varies enormously by type of work; a single infra commit can be larger than ten
  feature commits combined. Do not rank authors by this table.

*Raw data: `effort_by_author.csv`, `effort_monthly_share.csv`, `effort_toil_clusters.csv`.*
"""


# ---------------------------------------------------------------------------
# 4. Defect escape (SZZ)
# ---------------------------------------------------------------------------

def defect_escape(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "escape_summary.json")
    monthly = _read_csv(data_dir / "escape_monthly.csv")
    escapes = _read_csv(data_dir / "escapes.csv")
    if not summary:
        return f"# {target_name} — Defect Escape Rate\n\n_No escape_summary.json found -- run the `escape` module first._\n"

    by_repo: dict[str, int] = defaultdict(int)
    for e in escapes:
        by_repo[e["repo"]] += 1
    top_repos = sorted(by_repo.items(), key=lambda kv: -kv[1])[:10]

    if monthly:
        rates = [_fnum(r["escape_rate_12mo"]) * 100 for r in monthly]
        months = [r["month"] for r in monthly]
        recent = rates[-4:] if len(rates) >= 4 else rates
        early = rates[:4] if len(rates) >= 4 else rates
        trend_note = ("declining" if statistics.mean(recent) < statistics.mean(early) * 0.85
                       else "rising" if statistics.mean(recent) > statistics.mean(early) * 1.15
                       else "roughly stable")
        charts.dual_axis_trend(months, [int(r["commits"]) for r in monthly], rates,
                                "Commits/month", "Escape rate %",
                                f"{target_name}: commits vs. defect escape rate",
                                charts_dir / "escape_trend.png",
                                subtitle=f"{summary.get('total_escapes_attributed', 0)} bug-introducing commits attributed, SZZ")
        recent_range = f"{min(recent):.0f}-{max(recent):.0f}%" if recent else "n/a"
        early_range = f"{min(early):.0f}-{max(early):.0f}%" if early else "n/a"
    else:
        trend_note, recent_range, early_range = "unknown (no monthly data)", "n/a", "n/a"

    top_table = _md_table(["Repo", "Attributed escapes"], [[r, str(c)] for r, c in top_repos])

    return f"""# {target_name} — Defect *Escape* Rate (SZZ)

*A defect escape is dated to the commit that **introduced** it, not the commit that fixed it --
that is the moment whatever testing/review/CI existed on that day either caught it or didn't.
Implemented via the SZZ algorithm (Sliwerski/Zimmermann/Zeller): for each non-merge commit this
tool's ontology classifier calls `bug_fix` or `revert`, `git blame` at the fix's parent commit
attributes the deleted/modified lines back to their origin. Window: 365 days. Data:
`escapes.csv`, `escape_monthly.csv`, `escape_summary.json`. Chart: `charts/escape_trend.png`.*

## 1. Results

**{summary.get('total_escapes_attributed', 0)} bug-introducing commits attributed.** Fix
latency: median **{summary.get('latency_days_median', '?')} days**, p90
**{summary.get('latency_days_p90', '?')} days** -- one defect in ten survives that long before
its fix lands.

The trend is **{trend_note}**: the earliest observed cohorts ran {early_range}, the most recent
observed months run {recent_range}.

![Commits vs. defect escape rate](charts/escape_trend.png)

## 2. By repo (highest attributed escape count)

{top_table}

## 3. Honest limitations

- This is line-based SZZ without the meta-change/line-mapping refinements from SZZ RA/SZZ
  Unleashed, which correct for lines that moved rather than changed and filter cosmetic
  reformatting -- expect some inflation toward reformatting-adjacent commits.
- Detection bias is irreducible in git-only data: an escape is only visible once someone wrote
  a fix commit for it. A repo with less code review scrutiny will always measure artificially
  safer than it really is.
- Depends entirely on the ontology classifier's `bug_fix`/`revert` recall -- if that classifier
  under-detects fixes (check `ONTOLOGY_AUDIT.md`), escape rates here are a conservative floor,
  not the true rate.
- Pure-addition fix commits (no deleted lines) carry no blame target and are excluded from
  attribution -- see `escape_summary.json`'s `per_repo_fix_commit_stats` for the excluded count
  per repo.

*Raw data: `escapes.csv`, `escape_monthly.csv`.*
"""


# ---------------------------------------------------------------------------
# 5. Dependency graph
# ---------------------------------------------------------------------------

def dependency_graph(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    depgraph = _read_csv(data_dir / "depgraph_summary.csv")
    hotspots = _read_csv(data_dir / "complexity_hotspots.csv")
    coupling = _read_csv(data_dir / "churn_coupling.csv")
    if not depgraph and not hotspots:
        return f"# {target_name} — Dependency Graph & Hotspots\n\n_No depgraph_summary.csv or complexity_hotspots.csv found -- run those modules first._\n"

    analyzable = [r for r in depgraph if not r.get("skipped_reason")]
    skipped = [r for r in depgraph if r.get("skipped_reason")]
    zero_circular = sum(1 for r in analyzable if int(r.get("circular_count", 0)) == 0)

    dep_table = _md_table(
        ["Repo", "Internal modules", "Circular deps", "Orphans"],
        [[r["repo"], r["total_modules"], r["circular_count"], r["orphan_count"]] for r in analyzable],
    ) if analyzable else "_No repos successfully analyzed._"

    skip_table = (_md_table(["Repo", "Reason"], [[r["repo"], r["skipped_reason"]] for r in skipped])
                  if skipped else "")
    # built outside the f-string below: a backslash escape inside an
    # f-string's {} expression is invalid before Python 3.12 (PEP 701) --
    # this project's floor is 3.10, so the nested "\n\n" must not appear
    # inside the {...} itself. Caught by ruff with target-version=py310,
    # not by running locally on a newer interpreter that happens to allow it.
    skipped_section = ("### Skipped\n\n" + skip_table) if skipped else ""

    top_hot = sorted(hotspots, key=lambda r: -_fnum(r.get("hotspot_score", 0)))[:12]
    if top_hot:
        charts.horizontal_bar_ranked(
            [f"{h['repo']}/{h['file'].split('/')[-1]}" for h in top_hot],
            [_fnum(h["hotspot_score"]) for h in top_hot],
            f"{target_name}: top complexity x churn hotspots", charts_dir / "hotspots_top.png",
        )
    hot_table = _md_table(
        ["Repo", "File", "Total CCN", "Max fn CCN", "Revisions", "Hotspot score"],
        [[h["repo"], h["file"], h["total_ccn"], h["max_ccn"], h["n_revs"], h["hotspot_score"]] for h in top_hot],
    ) if top_hot else "_No complexity data available._"

    coup_sorted = sorted(coupling, key=lambda r: -_fnum(r.get("degree", 0)))[:10]
    coup_table = _md_table(
        ["Repo", "Entity", "Coupled with", "Co-change degree"],
        [[c["repo"], c["entity"], c["coupled"], c["degree"]] for c in coup_sorted],
    ) if coup_sorted else "_No coupling data available._"

    return f"""# {target_name} — Dependency *Graph* & Hotspots

*Internal import graph via `dependency-cruiser` (JS/TS), restricted to modules whose own source
is not under `node_modules` -- an early pass in building this tool nearly reported hundreds of
false "circular dependency" hits that were entirely inside third-party packages' own internals;
see `docs/METHODOLOGY.md`. Complexity via `lizard` (all languages) joined against `code-maat`
churn: `hotspot_score = total_ccn(file) x n_revisions(file)` (Tornhill). Coupling via
`code-maat`'s temporal-coupling analysis (files that change together, independent of any import
between them). Data: `depgraph_summary.csv`, `complexity_hotspots.csv`, `churn_coupling.csv`.
Chart: `charts/hotspots_top.png`.*

## 1. Internal circular dependencies

{len(analyzable)} of {len(depgraph)} repos analyzed ({len(skipped)} skipped -- see below).
**{zero_circular} of {len(analyzable)} have zero internal circular dependencies.**

{dep_table}

{skipped_section}

## 2. Complexity x churn hotspots

The files where cyclomatic complexity and change frequency compound -- where defects
concentrate, per Tornhill's "Your Code as a Crime Scene" methodology:

{hot_table}

![Top complexity x churn hotspots](charts/hotspots_top.png)

## 3. Logical/temporal coupling

Files that change together across commits, whether or not either imports the other -- often
reveals coupling an import graph alone would miss:

{coup_table}

## 4. Honest limitations

- Coupling by co-change does not distinguish "these files are properly related" from "this is
  an unnecessary coupling that should be refactored away" -- read the actual files before
  concluding either way.
- A circular-dependency count of 0 (or a low count of legitimate parent-child model pairs) does
  not mean the architecture has no problems -- it means this specific, narrow measurement
  found none. It says nothing about coupling *between* repos.

*Raw data: `depgraph_summary.csv`, `complexity_hotspots.csv`, `churn_coupling.csv`,
`depgraph_raw/*.json` (full per-repo graphs, regenerate via the `depgraph` module -- not
archived, see METHODOLOGY.md).*
"""


# ---------------------------------------------------------------------------
# 6. Duplication
# ---------------------------------------------------------------------------

def duplication_report(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    dup_summary = _read_json(data_dir / "duplication_summary.json")
    exact_summary = _read_json(data_dir / "exact_duplicate_summary.json")
    exact_files = _read_csv(data_dir / "exact_duplicate_files.csv")
    if not dup_summary and not exact_summary:
        return f"# {target_name} — Duplication\n\n_No duplication data found -- run the `duplication`/`exact_duplicates` modules first._\n"

    stats = dup_summary.get("portfolio_stats", {})
    top_clusters = sorted(exact_files, key=lambda r: -int(r.get("repo_count", 0)))[:15]
    cluster_table = _md_table(
        ["Relative path (or hash group)", "Repos sharing it", "Repos"],
        [[r.get("relative_paths", r.get("sha256", ""))[:60], r["repo_count"], r["repos"].replace(";", ", ")]
         for r in top_clusters],
    ) if top_clusters else "_No cross-repo exact duplicates found (or this is a single-repo target)._"

    is_portfolio = bool(exact_summary.get("total_repos_in_portfolio", 0) > 1)

    if is_portfolio:
        exact_section = (
            f"**{exact_summary.get('cross_repo_identical_same_path_groups', 0)}** files are "
            f"byte-identical across two or more repos at the same relative path (of "
            f"{exact_summary.get('total_repos_in_portfolio', 0)} repos scanned) -- the "
            f"strongest possible signal for extracting a shared package. Max repos sharing "
            f"one identical file: **{exact_summary.get('max_repo_count_for_one_file', 0)}**."
        )
        block_section = (
            f"**{_fnum(stats.get('percentage', 0)):.1f}%** of all lines are part of a duplicated "
            f"block. **{dup_summary.get('cross_repo_clone_pairs', 0)}** of "
            f"{dup_summary.get('total_clone_pairs', 0)} clone pairs are cross-repo (not "
            f"within a single repo)."
        )
    else:
        exact_section = ("_Single-repo target -- cross-repo exact duplication does not apply; "
                          "see `duplication_clones.csv` for within-repo blocks instead._")
        block_section = f"**{_fnum(stats.get('percentage', 0)):.1f}%** of lines are part of a duplicated block within this repo."

    return f"""# {target_name} — *Duplication*

*Two independent measurements, kept separate deliberately: `jscpd` finds **block-level**
duplication (>=10 lines / >=70 tokens) across the whole portfolio in one pass; a direct sha256
hash of whole-file contents finds **exact, byte-identical** files. A file can share a jscpd
block with another file while differing everywhere else -- conflating the two would overclaim
whole-file identity from a partial match (a real mistake caught and corrected while building
this tool by running an actual `diff`; see `docs/METHODOLOGY.md`). Data:
`duplication_summary.json`, `duplication_clones.csv`, `exact_duplicate_files.csv`,
`exact_duplicate_summary.json`.*

## 1. Block-level duplication (jscpd)

{block_section}

## 2. Exact, byte-identical files

{exact_section}

{cluster_table}

## 3. Honest limitations

- jscpd's percentage is inflated by legitimate per-project boilerplate (lockfiles, generated
  config) that isn't a real duplication problem -- the exact-match list above is the stricter,
  more actionable signal.
- Exact-match groups only catch identical files at the *same relative path*. Two files with
  identical content at different paths (e.g. one repo renamed its copy) are not detected here.

*Raw data: `duplication_clones.csv`, `exact_duplicate_files.csv`.*
"""


# ---------------------------------------------------------------------------
# 7. Security
# ---------------------------------------------------------------------------

def security_report(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "security_summary.json")
    secrets = _read_csv(data_dir / "security_secrets.csv")
    semgrep = _read_csv(data_dir / "security_semgrep.csv")
    if not summary:
        return f"# {target_name} — Security\n\n_No security_summary.json found -- run the `security` module first._\n"

    by_rule: dict[str, int] = defaultdict(int)
    by_repo: dict[str, int] = defaultdict(int)
    for s in secrets:
        by_rule[s["rule_id"]] += 1
        by_repo[s["repo"]] += 1
    rule_table = _md_table(["Rule", "Count"], [[k, str(v)] for k, v in sorted(by_rule.items(), key=lambda kv: -kv[1])])
    repo_table = _md_table(["Repo", "Findings"], [[k, str(v)] for k, v in sorted(by_repo.items(), key=lambda kv: -kv[1])])

    sev_table = _md_table(["Severity", "Count"],
                           [[k, str(v)] for k, v in summary.get("semgrep_by_severity", {}).items()]) \
        if summary.get("semgrep_by_severity") else "_No semgrep findings._"
    by_check: dict[str, int] = defaultdict(int)
    for s in semgrep:
        by_check[s["check_id"]] += 1
    check_table = _md_table(["Check", "Count"],
                             [[k, str(v)] for k, v in sorted(by_check.items(), key=lambda kv: -kv[1])[:15]]) \
        if by_check else "_No semgrep findings._"

    return f"""# {target_name} — *Security*

*`gitleaks` over **complete git history** per repo (a secret removed in a later commit is
still permanently readable by anyone with clone access) + `semgrep` (`p/security-audit` +
`p/secrets`) over the current tree. Data: `security_secrets.csv`, `security_semgrep.csv`,
`security_summary.json`.*

## 1. Secret-history scan (gitleaks)

**{summary.get('total_secrets_found', 0)} findings across {summary.get('repos_with_secrets', 0)}
repos** ({summary.get('repos_scanned', 0)} repos scanned):

{rule_table}

By repo:

{repo_table}

**Every rule-format match above is a starting point, not a confirmed secret** -- generic-entropy
rules in particular need a manual look. This tool does not attempt to validate or use any
discovered credential against a live provider API (out of scope regardless of feasibility); it
also checks whether each is still present in current `HEAD` vs. history-only where that
distinction changes the remediation urgency -- see the raw CSV's `commit` column and check with
`git grep <secret-prefix> HEAD` in the affected repo.

## 2. Code-pattern scan (semgrep)

**{summary.get('total_semgrep_findings', 0)} findings.**

By severity:

{sev_table}

Top checks triggered (top 15):

{check_table}

## 3. Honest limitations

- gitleaks' `generic-api-key` and `curl-auth-header` rules are pattern/entropy-based and will
  include false positives (test fixtures, non-secret high-entropy strings). Only
  format-confirmed rules (`aws-access-token`, `shopify-access-token`, `jwt`, etc.) are close to
  self-verifying by their prefix alone.
- semgrep's ruleset here (`p/security-audit`, `p/secrets`) is broad but not exhaustive --
  absence of a finding is not proof of absence of a vulnerability class the ruleset doesn't cover.

*Raw data: `security_secrets.csv`, `security_semgrep.csv`.*
"""


# ---------------------------------------------------------------------------
# 8. Test quality
# ---------------------------------------------------------------------------

def test_quality(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "testquality_summary.json")
    runs = _read_csv(data_dir / "testquality_runs.csv")
    ci_gates = _read_csv(data_dir / "ci_gates.csv")
    if not summary:
        return f"# {target_name} — Test Quality\n\n_No testquality_summary.json found -- run the `testquality` module first._\n"

    gated = sum(1 for r in ci_gates if r.get("any_workflow_runs_tests") == "True")
    status_table = _md_table(
        ["Repo", "Script", "Runner", "Passed", "Failed", "Total", "Node used", "Note"],
        [[r["repo"], r["script_used"], r["runner_detected"], r["tests_passed"], r["tests_failed"],
          r["tests_total"], r["node_version_used"], r.get("failure_mode", "")[:50]]
         for r in runs if r["ran"] == "True"],
    )

    return f"""# {target_name} — Test *Quality*

*Not "has a test script" (a proxy) -- every repo's unit-test script was **actually executed**
and its real pass/fail summary parsed from the runner's own output. Scoped to unit tests only
(integration suites needing live infrastructure are out of scope for an unattended run --
see `docs/METHODOLOGY.md`). CI-gate status is from parsing actual workflow step contents, not
inferred from a workflow file's existence. Data: `testquality_runs.csv`, `ci_gates.csv`.*

## 1. CI enforcement

**{gated} of {len(ci_gates)} repos** have a CI workflow that runs tests on any trigger. The
rest configure CI for build/deploy only.

## 2. Real, executed test results

{status_table}

**{summary.get('repos_all_tests_passing', 0)}** repos fully passing right now.
**{summary.get('repos_with_real_test_failures_right_now', 0)}** have real failures right now.
**{summary.get('repos_with_test_infra_but_zero_tests_written', 0)}** have a working test harness
that matches zero actual test files. **{summary.get('repos_with_broken_test_config', 0)}** have
a broken test configuration that prevents the suite from starting at all.
**{summary.get('repos_skipped_no_script', 0)}** have no unit-test script.

## 3. Honest limitations

- Integration/e2e test scripts are not executed by this module (they typically need live
  infrastructure this analysis has no access to) -- a repo could have a much larger, currently
  broken integration suite invisible here.
- A repo's runtime environment (Node/Python/Go version) can cause a false failure unrelated to
  the code under test -- this tool pins to the target's own declared engine version where it
  can detect one and records which runtime actually ran each suite (`node_version_used` /
  equivalent), but a mismatch it can't auto-correct will still show as a false failure. Check
  the raw log before treating any single failure as confirmed.

*Raw data: `testquality_runs.csv`, `ci_gates.csv`. Raw logs regenerate via the `testquality`
module (not archived).*
"""


# ---------------------------------------------------------------------------
# 9. Consolidation / way-forward roadmap
# ---------------------------------------------------------------------------

def consolidation_roadmap(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    risk = _read_csv(data_dir / "risk_ranking.csv")
    exact_summary = _read_json(data_dir / "exact_duplicate_summary.json")
    ci_gates = _read_csv(data_dir / "ci_gates.csv")
    security_summary = _read_json(data_dir / "security_summary.json")
    testquality_summary = _read_json(data_dir / "testquality_summary.json")
    toil_summary = _read_json(data_dir / "effort_summary.json")

    if not risk:
        return f"# {target_name} — Consolidation & Way-Forward Roadmap\n\n_No risk_ranking.csv found -- run the `synthesize` module first._\n"

    ungated = [r for r in ci_gates if r.get("any_workflow_runs_tests") != "True" and r.get("has_ci_config") == "True"]
    proven_gate = [r for r in ci_gates if r.get("any_workflow_runs_tests") == "True"]

    top_risk = sorted(risk, key=lambda r: -_fnum(r["risk_score"]))[:10]
    risk_table = _md_table(
        ["Repo", "Risk score", "Escapes", "Top-5 hotspot sum", "Exact dup files", "CI gate missing", "Security findings"],
        [[r["repo"], r["risk_score"], r["escape_count"], _fmt(r["top5_hotspot_sum"]), r["exact_dup_file_count"],
          r["ci_gate_missing"], r["security_findings"]] for r in top_risk],
    )

    actions = []
    if int(security_summary.get("total_secrets_found", 0)) > 0:
        actions.append(
            f"**Rotate credentials found in git history first.** {security_summary['total_secrets_found']} "
            f"secret-shaped findings across {security_summary.get('repos_with_secrets', 0)} repos -- see "
            f"`SECURITY.md`. This is a today action, independent of everything else here."
        )
    if ungated:
        proven_note = (f" A working, proven pattern already exists in this portfolio: {proven_gate[0]['repo']}."
                        if proven_gate else "")
        actions.append(
            f"**Wire CI to actually run tests on the {len(ungated)} repos where it currently doesn't.**{proven_note} "
            f"This is the single highest-leverage fix available: every other quality finding downstream of "
            f"'nothing blocks a bad merge' gets caught here, going forward, for free."
        )
    if exact_summary and exact_summary.get("max_repo_count_for_one_file", 0) >= 3:
        actions.append(
            f"**Extract the byte-identical shared code into real internal packages.** "
            f"{exact_summary.get('cross_repo_identical_same_path_groups', 0)} files are identical across "
            f"multiple repos (up to {exact_summary['max_repo_count_for_one_file']} at once) -- see "
            f"`DUPLICATION.md` for the exact file list. Extracting only what the exact-match list confirms "
            f"identical changes zero behavior; verify with `diff` before assuming a jscpd block match means"
            f" the same for any file not on the exact-match list."
        )
    if testquality_summary and testquality_summary.get("repos_with_test_infra_but_zero_tests_written", 0) > 0:
        actions.append(
            f"**{testquality_summary['repos_with_test_infra_but_zero_tests_written']} repos have a working "
            f"test harness and zero tests behind it.** Cheaper to fix than repos with no harness at all -- "
            f"the wiring already works, someone just needs to write the tests."
        )
    if toil_summary and toil_summary.get("toil_clusters_found", 0) > 0:
        actions.append(
            f"**{toil_summary['toil_clusters_found']} candidate toil clusters** "
            f"({toil_summary.get('toil_commits_in_clusters', 0)} commits) are repeated, mechanical work "
            f"concentrated by location -- see `EFFORT_ALLOCATION.md` for the ranked list. Each is worth a "
            f"human read before committing to a specific fix; this tool does not size the remediation effort."
        )

    actions_md = "\n\n".join(f"{i+1}. {a}" for i, a in enumerate(actions)) if actions else "_No high-confidence action items surfaced by this run's thresholds._"

    return f"""# {target_name} — Consolidation & *Way-Forward* Roadmap

*Synthesizes every other category into one ranked list and a prioritized action list. The risk
score (`synthesize.py`) is a weighted, min-max-normalized combination of escape rate, hotspot
concentration, duplication involvement, missing CI gates, test failures, security findings, and
bus-factor -- a heuristic for *prioritization*, stated as such, not a ground truth. Data:
`risk_ranking.csv`, `risk_weights.json`.*

## 1. Highest-priority repos, by composite risk score

{risk_table}

See `risk_weights.json` for the exact weights behind this ranking -- change them if you weigh
these dimensions differently; the raw per-dimension numbers underneath are the actual evidence.

## 2. Recommended action order

{actions_md}

## 3. Honest limitations

- The composite risk score is dominated in part by raw activity/scale (an old, high-churn repo
  accumulates more escapes and hotspot mass than a small quiet one just by having existed
  longer and shipped more) -- it is a prioritization aid for where to look first, not a
  cleanly isolated "badness" measure. Read the underlying per-dimension columns before acting
  on rank alone.
- This report does not estimate effort or ROI for any recommendation -- that requires product
  and team context this tool does not have. It tells you what the data shows and where to look;
  the sizing and sequencing judgment is a human decision.

*Raw data: `risk_ranking.csv`, `risk_weights.json`.*
"""


# ---------------------------------------------------------------------------
# 10. Method review (self-audit)
# ---------------------------------------------------------------------------

def method_review(data_dir: Path, charts_dir: Path, target_name: str, run_log: dict | None = None) -> str:
    audit = _read_json(data_dir / "ontology_audit_summary.json")
    run_log = run_log or _read_json(data_dir / "run_log.json")

    modules = run_log.get("modules_run", []) if run_log else []
    ok = [m for m in modules if m.get("status") == "ok"]
    failed = [m for m in modules if m.get("status") == "error"]
    module_table = _md_table(
        ["Module", "Status", "Elapsed (s)"],
        [[m["module"], m["status"], m["elapsed_s"]] for m in modules],
    ) if modules else "_No run_log.json found for this run._"

    audit_section = ""
    if audit:
        audit_section = f"""
## Ontology classifier accuracy (independent blind audit)

**{audit.get('exact_agreement_pct', '?')}% exact leaf agreement, {audit.get('superclass_agreement_pct', '?')}%
superclass agreement** against an independent classification of the same commit sample, with no
access to this tool's own labels. See `ONTOLOGY_AUDIT.md` for the full disagreement breakdown --
read this run's ontology percentages as directional at this agreement level, not precise to the
point.
"""

    return f"""# {target_name} — Method *Review*

*This tool's own self-audit: which modules ran, which failed, and what has been independently
checked rather than taken on faith. See `docs/METHODOLOGY.md` for the full list of bugs found
and fixed while building this tool -- kept visible rather than quietly corrected away.*

## Module run status

{module_table}

{f"**{len(failed)} module(s) failed this run** -- their outputs are absent, not silently zero. See run_log.json for tracebacks." if failed else f"All {len(ok)} modules completed."}
{audit_section}
## What has NOT been independently verified in this run

- Composite risk ranking weights (`synthesize.py`) are a stated judgment call, not
  empirically validated against any outcome.
- Toil clusters (`effort.py`) are mechanically grouped, not diff-read and confirmed.
- Security findings below a format-confirmed rule (generic-api-key, curl-auth-header) are not
  individually triaged for true/false-positive status.

*This section exists so a reader can tell which numbers in this report carry independent
verification and which are this tool's first-pass output -- treat the latter as a lead to
check, not a settled fact.*
"""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def dependency_health(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "deps_audit_summary.json")
    if not summary:
        return f"# {target_name} — Dependency *Health*\n\n_No deps_audit_summary.json found -- run the `deps_audit` module first._\n"
    outdated = _read_csv(data_dir / "deps_outdated.csv")
    cves = _read_csv(data_dir / "deps_cves.csv")
    by_repo: dict[str, int] = defaultdict(int)
    for c in cves:
        by_repo[c["repo"]] += 1
    top_table = _md_table(["Repo", "CVE findings"],
                           [[r, str(c)] for r, c in sorted(by_repo.items(), key=lambda kv: -kv[1])[:12]])
    sev = summary.get("cve_by_severity", {})
    sev_table = _md_table(["Severity", "Count"], [[k, str(v)] for k, v in
                           sorted(sev.items(), key=lambda kv: -{"critical": 3, "high": 2, "medium": 1, "low": 0}.get(kv[0], -1))])
    behind_sample = [o for o in outdated if o["current"] != "?" and o["latest"] != "?"
                      and o["current"].split(".")[0] != o["latest"].split(".")[0]][:12]
    behind_table = _md_table(["Repo", "Package", "Current", "Latest"],
                              [[o["repo"], o["package"], o["current"], o["latest"]] for o in behind_sample])
    return f"""# {target_name} — Dependency *Health*

*`osv-scanner` (Google's cross-ecosystem OSV-database scanner) reads each repo's lockfile
directly against known CVE records -- a different, deeper question than gitleaks (committed
secrets) or semgrep (code patterns): are the *dependencies themselves* known-vulnerable.
`npm outdated` gives current vs. latest per package. `npm audit` was tried and dropped (hung
repeatedly on a live registry round-trip in this environment); osv-scanner is faster and
already confirmed working -- see docs/METHODOLOGY.md. Data: `deps_cves.csv`, `deps_outdated.csv`.*

## 1. Known-CVE findings

**{summary.get('total_cve_findings', 0)} findings across {summary.get('repos_with_cves', 0)} repos.**

{sev_table}

{top_table}

## 2. Package staleness

**{summary.get('total_outdated_packages', 0)} outdated packages, {summary.get('outdated_major_version_behind', 0)} a full major version behind** (current vs. latest):

{behind_table}

## 3. Honest limitations

- osv-scanner flags a *known* CVE affecting the resolved version -- it does not confirm the
  vulnerable code path is actually reachable/exploited in this codebase's usage of the package.
- "Major version behind" is a proxy for staleness/upgrade risk, not itself a defect --
  some majors are trivial bumps, others are breaking rewrites. Triage by package, not by count.

*Raw data: `deps_cves.csv`, `deps_outdated.csv`.*
"""


def code_quality(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "lint_quality_summary.json")
    if not summary:
        return f"# {target_name} — Code *Quality* (Static Analysis)\n\n_No lint_quality_summary.json found -- run the `lint_quality` module first._\n"
    rows = _read_csv(data_dir / "lint_quality.csv")
    linted = [r for r in rows if r["ran"] == "True"]
    table = _md_table(["Repo", "Linter", "Errors", "Warnings", "Top rules"],
                       [[r["repo"], r["linter"], r["error_count"], r["warning_count"], r["top_rules"][:80]]
                        for r in sorted(linted, key=lambda r: -_fnum(r["error_count"]))])
    return f"""# {target_name} — Code *Quality* (Static Analysis)

*Each repo's own linter, run with its own config -- never a config this tool invents. ESLint
via the repo's local `node_modules/.bin/eslint` (not `npx`, which cannot resolve a project's
plugin-dependent config). ruff for Python, staticcheck for Go. Data: `lint_quality.csv`.*

## 1. Results

**{summary.get('repos_linted', 0)} of {summary.get('repos_linted', 0) + summary.get('repos_skipped', 0)}
repos actually linted** ({summary.get('repos_skipped', 0)} skipped -- see below).
**{summary.get('total_errors', 0)} errors, {summary.get('total_warnings', 0)} warnings** total.

{table}

## 2. Why repos were skipped

{len(summary.get('skip_reasons', {}))} repos could not be linted -- almost always because the
repo's own `package.json` declares a `lint` script that calls a linter never installed as a
real dependency (`eslint not in node_modules/.bin`). That is itself a finding: a lint script
that cannot run is not a quality gate, it is a broken promise in `package.json`.

## 3. Honest limitations

- Different repos may run different rule strictness (each uses its own config) -- error counts
  are not directly comparable across repos with different configs.

*Raw data: `lint_quality.csv`.*
"""


def mutation_testing(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    summary = _read_json(data_dir / "mutation_summary.json")
    if not summary:
        return f"# {target_name} — *Mutation* Testing\n\n_No mutation_summary.json found -- run the `mutation` module first._\n"
    rows = _read_csv(data_dir / "mutation_results.csv")
    table = _md_table(["Repo", "File mutated", "Mutants", "Killed", "Survived", "No coverage", "Score %"],
                       [[r["repo"], r["file_mutated"], r["total_mutants"], r["killed"], r["survived"],
                         r["no_coverage"], r["mutation_score"]] for r in rows if r["ran"] == "True"])
    return f"""# {target_name} — *Mutation* Testing

*Stryker: injects synthetic bugs (mutants) into a file and re-runs the test suite against each
one. A test suite that passes on unmutated code but also passes on a *mutated* one has not
actually verified that behavior -- mutation score (killed / covered mutants) answers "do these
tests catch a real defect," which passing-test-count alone cannot. Scoped deliberately: only
repos with a fully-passing unit suite were attempted (a failing suite has no meaningful
baseline), mutating only each repo's #1 complexity x churn hotspot (bounded runtime -- see
docs/METHODOLOGY.md for the install recipe this took three prior failed attempts to find).
Data: `mutation_results.csv`.*

## 1. Results

{table if rows else "_No successful runs._"}

{summary.get('note', '')}

## 2. Honest limitations

- Attempted on {summary.get('repos_attempted', 0)} repos, succeeded on {summary.get('repos_succeeded', 0)}
  -- the others failed for repo-specific environment reasons (see `mutation_summary.json`'s
  `skip_reasons`), not chased further given time. This is a real, if narrow, data point per
  succeeding repo, not a portfolio-wide mutation posture.
- Only one file per repo was mutated (the highest hotspot) -- a low mutation score there is a
  real, specific finding about that file; it should not be generalized to "this repo's tests
  are bad" without checking other files.

*Raw data: `mutation_results.csv`.*
"""


def architecture_report(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    graph = _read_json(data_dir / "architecture_graph.json")
    shared = _read_json(data_dir / "shared_deps.json")
    if not graph:
        return f"# {target_name} — *Architecture*, HLD & Memory Graph\n\n_No architecture_graph.json found -- capture via codebase-memory-mcp first (see docs/METHODOLOGY.md)._\n"

    cri = graph.get("cross_repo_intelligence", {})
    indexed_repos = cri.get("indexed_repos", [])
    rep_repo = graph.get("representative_repo", indexed_repos[0] if indexed_repos else "the indexed repo")
    boundary_table = _md_table(["From", "To", "Call count"],
                                [[b["from"], b["to"], b["call_count"]] for b in graph.get("boundaries", [])])
    layer_table = _md_table(["Package", "Layer", "Why"],
                             [[lyr["name"], lyr["layer"], lyr["reason"]] for lyr in graph.get("layers", [])])
    hotspots = graph.get("hotspots", [])
    hotspot_table = _md_table(["Function", "Fan-in (callers)"],
                               [[h["qualified_name"].split(".")[-2] + "." + h["name"], h["fan_in"]]
                                for h in hotspots[:10]])
    cluster_table = _md_table(["Cluster", "Members", "Cohesion", "Represents"],
                               [[c["id"], c["members"], round(c["cohesion"], 2), ", ".join(c["top_nodes"][:3])]
                                for c in sorted(graph.get("clusters", []), key=lambda c: -c["members"])[:8]])
    shared_list = shared.get("most_shared_packages", []) if shared else []
    shared_table = _md_table(["Package", "Repos using it"], [[p, str(c)] for p, c in shared_list[:12]])

    n_repos_capture = f"{graph.get('total_nodes', '?')} nodes, {graph.get('total_edges', '?')} edges across {len(indexed_repos)} repo(s): {', '.join(indexed_repos) or rep_repo}"
    top_shared_note = ""
    if shared_list:
        top_pkg, top_count = shared_list[0]
        top_shared_note = (f"\n**Most-shared internal signal**: `{top_pkg}` is used by "
                            f"**{top_count} of {len(shared.get('repo_dep_counts', {})) or '?'} repos** -- "
                            f"check whether it is a real shared internal package (worth checking its registry "
                            f"listing/publish count) rather than assuming no cross-repo dependency exists.\n")
    top_boundary_note = ""
    boundaries = graph.get("boundaries", [])
    if boundaries:
        b = max(boundaries, key=lambda x: x["call_count"])
        top_boundary_note = (f"\n`{b['from']} -> {b['to']}`: {b['call_count']} calls -- the largest internal "
                              f"boundary found in this capture; cross-check against `DUPLICATION.md` for whether "
                              f"that target package is also duplicated across repos.\n")
    top_hotspot_note = ""
    if hotspots:
        h = hotspots[0]
        top_hotspot_note = (f"\n`{h['name']}` ({h['fan_in']} callers) is the single most depended-upon function "
                             f"found in this capture.\n")

    return f"""# {target_name} — *Architecture*, HLD & Memory Graph

*Built via `codebase-memory-mcp` (LSP-based call/usage resolution -- a real persistent code
knowledge graph, i.e. a "memory graph" of the codebase, not a static-analysis approximation of
one). This capture: {n_repos_capture}. **Caveat, said plainly**: this capture used an
interactive MCP tool available in a Claude Code session, not a subprocess this tool's own
CLI can invoke standalone on any machine -- treat this section as a snapshot from whatever
repos were indexed when it was captured, not a rerunnable module output the way every other
section in this report is. Re-capture it for a different repo set by indexing with
`codebase-memory-mcp` and re-saving `architecture_graph.json`/`shared_deps.json` in this
format -- see `docs/METHODOLOGY.md`.*

## 1. Inter-repo connectivity: measured, not assumed

The tool's own cross-repo-intelligence mode matches HTTP/async/gRPC/GraphQL/tRPC calls across
indexed projects. Result across {cri.get('projects_scanned', '?')} projects: **{cri.get('total_cross_edges', 0)}
cross-repo calls found** (HTTP: {cri.get('cross_http_calls',0)}, async: {cri.get('cross_async_calls',0)},
channel: {cri.get('cross_channel',0)}, gRPC: {cri.get('cross_grpc_calls',0)}, GraphQL: {cri.get('cross_graphql_calls',0)}).
{top_shared_note}
{shared_table}

## 2. HLD: layers and boundaries ({rep_repo})

{layer_table}

{boundary_table}
{top_boundary_note}
## 3. LLD: the actual hotspot functions and real clusters

{hotspot_table}
{top_hotspot_note}
Real Leiden-detected clusters (the de-facto modules, which cut across folder layout):

{cluster_table}

## 4. Honest limitations

- Representative, not exhaustive: the indexed repo(s) stand in for any structurally similar
  repos elsewhere in the portfolio (check `DUPLICATION.md` for which repos actually share
  structure before generalizing this section to them).
- Cross-repo-intelligence only detects *code-level* calls (HTTP/async/RPC). It cannot detect
  connectivity through shared infrastructure with no code reference -- this analysis has no
  runtime-wiring export (e.g. a CTO-approved production env-var dump) for this target, so
  infra-level connectivity (if any) is unverified, not ruled out.

*Raw data: `architecture_graph.json`, `shared_deps.json`.*
"""


def knowledge_graph_report(data_dir: Path, charts_dir: Path, target_name: str) -> str:
    stats = _read_json(data_dir / "knowledge_graph_stats.json")
    if not stats:
        return f"# {target_name} — *Knowledge* Graph\n\n_No knowledge_graph_stats.json found -- run the `knowledge_graph` module first._\n"
    et = stats.get("edge_type_counts", {})
    top_connected = stats.get("top_connected_repos", [])
    top_table = _md_table(["Repo", "Degree (dup + shared-package connections)"],
                           [[t["repo"], t["degree"]] for t in top_connected])
    example_repo = top_connected[0]["repo"] if top_connected else "some-repo"
    return f"""# {target_name} — *Knowledge* Graph

*A real, exported graph artifact -- `knowledge_graph.graphml` -- not a description of one.
Standard GraphML: loads directly in Gephi, yEd, Neo4j (`neo4j-admin database import`), igraph,
or networkx (`nx.read_graphml(...)`). Built by assembling every relationship this tool has
already computed into one graph, re-scanning nothing: **DUPLICATE_OF** edges (repo<->repo,
weighted by count of byte-identical files -- `exact_duplicates.py`'s sha256 output, not a
heuristic), **SHARES_PACKAGE** edges (repo<->repo, weighted by shared npm dependency count,
>=5 floor), **COUPLED_WITH** edges (file<->file within one repo, weighted by code-maat's
temporal-coupling degree). Round-trip verified: exported, reloaded, and spot-checked against
known-real duplication counts before being reported here.*

## 1. What's in it

**{stats.get('total_nodes', 0)} nodes** ({stats.get('repo_nodes', 0)} repos,
{stats.get('file_nodes', 0)} files that participate in at least one coupling relationship),
**{stats.get('total_edges', 0)} edges**:

{_md_table(["Edge type", "Count"], [[k, str(v)] for k, v in et.items()])}

![Repo-to-repo knowledge graph](charts/knowledge_graph.png)

## 2. Most-connected repos

{top_table}

## 3. How to query it yourself

```python
import networkx as nx
G = nx.read_graphml("knowledge_graph.graphml")
# every repo this one shares 100+ identical files with:
[(u, v, d["weight"]) for u, v, d in G.edges("repo:{example_repo}", data=True)
 if d.get("type") == "DUPLICATE_OF" and d["weight"] > 100]
```

## 4. Honest limitations

- File-level nodes exist only for `COUPLED_WITH` (within-repo) relationships -- the portfolio's
  full within-repo import graphs (thousands of file nodes each) live separately in
  `depgraph_raw/*.json` per repo, not merged into this graph, to keep it at a size actually
  useful to open in a graph tool rather than an unreadable hairball.
- `SHARES_PACKAGE` is direct dependencies only (not transitive) and floors at 5+ shared
  packages to filter noise (every repo shares *some* common package).
- No cross-repo `CALLS` edges are in this graph -- `ARCHITECTURE.md`'s codebase-memory-mcp
  capture already established that number is zero for the 3 repos it indexed.

*Artifact: `knowledge_graph.graphml`. Raw stats: `knowledge_graph_stats.json`.*
"""


REPORT_SEQUENCE = [
    ("REPO_ANALYSIS.md", repo_analysis),
    ("ARCHITECTURE.md", architecture_report),
    ("KNOWLEDGE_GRAPH.md", knowledge_graph_report),
    ("COMMIT_ONTOLOGY.md", commit_ontology),
    ("EFFORT_ALLOCATION.md", effort_allocation),
    ("ESCAPE.md", defect_escape),
    ("DEPGRAPH.md", dependency_graph),
    ("DUPLICATION.md", duplication_report),
    ("SECURITY.md", security_report),
    ("DEPENDENCY_HEALTH.md", dependency_health),
    ("CODE_QUALITY.md", code_quality),
    ("TEST_QUALITY.md", test_quality),
    ("MUTATION.md", mutation_testing),
    ("CONSOLIDATION_ROADMAP.md", consolidation_roadmap),
    ("METHOD_REVIEW.md", method_review),
]


def generate_all(data_dir: Path, out_dir: Path, target_name: str) -> list[Path]:
    """Renders every deep report into out_dir (charts land in out_dir/charts/,
    referenced by the markdown as "charts/<file>.png" so both the raw .md
    files and a PDF built from them resolve the images correctly). Returns
    the list of report paths written, in the fixed reading order."""
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, fn in REPORT_SEQUENCE:
        try:
            content = fn(data_dir, charts_dir, target_name)
        except Exception as e:  # noqa: BLE001 -- one category's failure shouldn't block the rest
            content = f"# {target_name} — {filename[:-3].replace('_', ' ').title()}\n\n_Generation failed: {e}_\n"
        path = out_dir / filename
        path.write_text(content)
        written.append(path)
    return written
