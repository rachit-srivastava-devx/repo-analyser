"""Effort allocation: what engineers' commits actually go to, per author and
over time, plus automated toil-cluster detection.

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
"""
from __future__ import annotations

import csv
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


def run_effort(ontology_csv: Path, out_dir: Path) -> Path:
    commits = _read_ontology(ontology_csv)
    if not commits:
        raise ValueError(f"{ontology_csv} has no rows -- run the ontology module first")

    authors = per_author_breakdown(commits)
    author_path = out_dir / "effort_by_author.csv"
    write_csv(author_path, [asdict(a) for a in authors])

    monthly = monthly_superclass_share(commits)
    write_csv(out_dir / "effort_monthly_share.csv", monthly)

    clusters = detect_toil_clusters(commits)
    write_csv(out_dir / "effort_toil_clusters.csv", clusters,
              fieldnames=["repo", "primary_dir", "superclass", "dominant_leaf", "commit_count",
                          "distinct_authors", "first_seen", "last_seen", "sample_subjects"] if clusters else None)

    total = len(commits)
    delivery_authors = [a for a in authors if a.total_commits >= 20]
    median_delivery = (sorted(a.delivery_pct for a in delivery_authors)[len(delivery_authors) // 2]
                        if delivery_authors else 0.0)
    write_json(out_dir / "effort_summary.json", {
        "total_commits": total,
        "total_authors": len(authors),
        "authors_with_20plus_commits": len(delivery_authors),
        "median_delivery_pct_20plus_commit_authors": median_delivery,
        "toil_clusters_found": len(clusters),
        "toil_cluster_min_size": TOIL_MIN_CLUSTER_SIZE,
        "toil_commits_in_clusters": sum(c["commit_count"] for c in clusters),
    })
    return author_path
