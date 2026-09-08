"""Effort allocation: what engineers' commits actually go to, per author and
over time, plus automated toil-cluster detection and portfolio-wide
contribution concentration.

This is one category a hand-built reference analysis this tool was originally
modeled on covered that this tool's first version didn't. Two differences
from that manual analysis, stated rather than hidden:

1. Toil clusters there were found by an analyst reading representative
   diffs by hand for a handful of hand-picked concentrations. Here they're
   found mechanically: non-delivery commits are grouped by (superclass, the
   touched files' top-2 path segments) and any group above a size
   threshold is reported as a candidate cluster. This trades verified
   precision for full, automatic coverage -- a cluster reported here is a
   *candidate* worth a human diff-read, not a confirmed finding the way a
   hand-reviewed one is.
2. No per-cluster "estimated recovery" or "build effort" sizing -- that
   requires judgment about a specific remediation, which this module does
   not have enough context to make up. `synthesize.py`/the roadmap layer
   is where a human-authored effort estimate belongs.

`run_effort` is invoked exactly once per `analyze` run, over one ontology CSV
that already holds every repo passed to that run (see `ontology.py`'s
`run_ontology`, and `cli.py`'s single `run_effort(out_dir /
"ontology_commits.csv", out_dir)` call -- no per-repo loop). That means
`per_author_breakdown`'s `total_commits` is already each author's commit
count summed across the whole run, whether that run covers one repo or a
portfolio -- there is nothing further to sum here, just a Gini coefficient
over numbers that already exist. Onboarding-time-to-first-commit is
deliberately out of scope: git has no "repo access granted" timestamp, so
there is no honest proxy for it to compute.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.util import write_csv, write_json


def _read_ontology(ontology_csv: Path) -> list[dict]:
    with open(ontology_csv) as f:
        return list(csv.DictReader(f))


@dataclass
class AuthorEffort:
    author: str
    total_commits: int
    delivery_pct: float
    correction_pct: float
    code_health_pct: float
    ops_config_pct: float
    data_schema_pct: float
    housekeeping_pct: float
    other_pct: float


def per_author_breakdown(commits: list[dict]) -> list[AuthorEffort]:
    by_author: dict[str, list[dict]] = defaultdict(list)
    for c in commits:
        by_author[c["author"]].append(c)

    rows = []
    for author, rows_for_author in by_author.items():
        n = len(rows_for_author)
        counts: dict[str, int] = defaultdict(int)
        for c in rows_for_author:
            counts[c["superclass"]] += 1
        rows.append(AuthorEffort(
            author=author, total_commits=n,
            delivery_pct=round(100 * counts.get("delivery", 0) / n, 2),
            correction_pct=round(100 * counts.get("correction", 0) / n, 2),
            code_health_pct=round(100 * counts.get("code_health", 0) / n, 2),
            ops_config_pct=round(100 * counts.get("ops_config", 0) / n, 2),
            data_schema_pct=round(100 * counts.get("data_schema", 0) / n, 2),
            housekeeping_pct=round(100 * counts.get("housekeeping", 0) / n, 2),
            other_pct=round(100 * counts.get("other", 0) / n, 2),
        ))
    rows.sort(key=lambda r: -r.total_commits)
    return rows


def monthly_superclass_share(commits: list[dict]) -> list[dict]:
    by_month: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in commits:
        month = c["date"][:7]
        by_month[month][c["superclass"]] += 1
    rows = []
    for month in sorted(by_month):
        counts = by_month[month]
        total = sum(counts.values())
        row = {"month": month, "total_commits": total}
        for sc in ("delivery", "correction", "code_health", "ops_config",
                   "data_schema", "housekeeping", "other"):
            row[sc] = round(counts.get(sc, 0) / total, 4) if total else 0.0
        rows.append(row)
    return rows


TOIL_MIN_CLUSTER_SIZE = 15
NON_TOIL_SUPERCLASSES = {"delivery"}  # delivery is product work, not toil, by definition


def detect_toil_clusters(commits: list[dict]) -> list[dict]:
    """Groups non-delivery commits by (repo, primary_dir, superclass) --
    where in the tree the toil concentrates, not just what category it is
    -- and flags any group at or above TOIL_MIN_CLUSTER_SIZE as a
    candidate toil cluster. `primary_dir` (from ontology.py) is the most
    common up-to-2-segment directory prefix among a commit's touched
    files, so e.g. "62 ops_config commits under src/api/admin" is visible
    as one cluster rather than being invisible inside a repo-wide count.

    This is mechanical clustering, not a verified finding: every count is
    a real, rerunnable group-by, but unlike a hand-reviewed toil deep-dive,
    nobody has read representative diffs for each cluster here. Treat each
    row as "worth a human diff-read," not confirmed."""
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for c in commits:
        if c["superclass"] in NON_TOIL_SUPERCLASSES or not c.get("primary_dir"):
            continue
        key = (c["repo"], c["primary_dir"], c["superclass"])
        groups[key].append(c)

    clusters = []
    for (repo, primary_dir, superclass), items in groups.items():
        if len(items) < TOIL_MIN_CLUSTER_SIZE:
            continue
        authors = {i["author"] for i in items}
        dates = sorted(i["date"] for i in items)
        leaf_counts: dict[str, int] = defaultdict(int)
        for i in items:
            leaf_counts[i["leaf"]] += 1
        dominant_leaf = max(leaf_counts.items(), key=lambda kv: kv[1])[0]
        clusters.append({
            "repo": repo, "primary_dir": primary_dir, "superclass": superclass,
            "dominant_leaf": dominant_leaf, "commit_count": len(items),
            "distinct_authors": len(authors),
            "first_seen": dates[0][:10], "last_seen": dates[-1][:10],
            "sample_subjects": " | ".join(i["subject"][:80] for i in items[:3]),
        })
    clusters.sort(key=lambda c: -c["commit_count"])
    return clusters


def _gini(counts: list[int]) -> float:
    """Gini coefficient of a distribution of non-negative counts (here: each
    author's total commit count across the whole run). Identical formula to
    `collectors/inventory.py`'s `_gini` (bus-factor, computed per repo) --
    reimplemented locally rather than imported, per this codebase's
    convention of not reaching for another module's private `_`-prefixed
    helper (see `escape.py` importing `ontology.classify_commit`, a *public*
    function, for the one documented exception).

    G = (2 * sum((i+1) * x_i) / (n * sum(x_i))) - (n+1)/n, x_i = each
    author's commit count sorted ascending, i = 0-indexed rank. G=0 is
    perfectly even authorship; G->1 is one author owns everything.
    """
    if not counts or sum(counts) == 0:
        return 0.0
    xs = sorted(counts)
    n = len(xs)
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 4)


def _top_decile_share(counts: list[int]) -> tuple[int, float]:
    """How much of the total a top decile of contributors holds: sort
    counts descending, take the top ceil(10% of len(counts)) entries
    (minimum 1, so this is defined even for a single-author run), and
    return (how many authors that was, their combined share of the total).
    Returning the author count alongside the share is what makes the share
    reproducible by hand from `effort_by_author.csv` (sorted the same way)
    without having to guess how "top 10%" was rounded.
    """
    if not counts or sum(counts) == 0:
        return 0, 0.0
    xs_desc = sorted(counts, reverse=True)
    n = len(xs_desc)
    k = max(1, math.ceil(n * 0.1))
    return k, round(sum(xs_desc[:k]) / sum(xs_desc), 4)


def run_effort(ontology_csv: Path, out_dir: Path) -> Path:
    commits = _read_ontology(ontology_csv)
    if not commits:
        raise ValueError(f"{ontology_csv} has no rows -- run the ontology module first")

    authors = per_author_breakdown(commits)
    author_path = out_dir / "effort_by_author.csv"
    write_csv(author_path, [asdict(a) for a in authors], fieldnames=AuthorEffort)

    monthly = monthly_superclass_share(commits)
    write_csv(out_dir / "effort_monthly_share.csv", monthly,
              fieldnames=["month", "total_commits", "delivery", "correction", "code_health",
                          "ops_config", "data_schema", "housekeeping", "other"])

    clusters = detect_toil_clusters(commits)
    write_csv(out_dir / "effort_toil_clusters.csv", clusters,
              fieldnames=["repo", "primary_dir", "superclass", "dominant_leaf", "commit_count",
                          "distinct_authors", "first_seen", "last_seen", "sample_subjects"])

    total = len(commits)
    delivery_authors = [a for a in authors if a.total_commits >= 20]
    median_delivery = (sorted(a.delivery_pct for a in delivery_authors)[len(delivery_authors) // 2]
                        if delivery_authors else 0.0)

    # Portfolio-wide contribution concentration: `authors` already holds each
    # author's total commit count summed across every repo this run covered
    # (see module docstring -- there is one `run_effort` call per run, over
    # one already-merged ontology CSV), so no further cross-repo summation is
    # needed here; this is the same `_gini` formula `inventory.py` applies
    # per repo for bus-factor, applied instead to that portfolio-wide list.
    # Checkable by hand from effort_by_author.csv's total_commits column
    # together with total_commits/total_authors above.
    author_commit_counts = [a.total_commits for a in authors]
    contribution_gini = _gini(author_commit_counts)
    top_decile_count, top_decile_share = _top_decile_share(author_commit_counts)

    write_json(out_dir / "effort_summary.json", {
        "total_commits": total,
        "total_authors": len(authors),
        "authors_with_20plus_commits": len(delivery_authors),
        "median_delivery_pct_20plus_commit_authors": median_delivery,
        "toil_clusters_found": len(clusters),
        "toil_cluster_min_size": TOIL_MIN_CLUSTER_SIZE,
        "toil_commits_in_clusters": sum(c["commit_count"] for c in clusters),
        "contribution_gini_portfolio_wide": contribution_gini,
        "contribution_top10pct_author_count": top_decile_count,
        "contribution_top10pct_commit_share": top_decile_share,
    })
    return author_path
