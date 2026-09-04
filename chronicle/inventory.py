"""Repo tiering & activity: commit velocity, tenure, bus factor.

Uses plain `git log` (not PyDriller) deliberately: this pass needs only
commit metadata (hash/author/date/parents), not diffs, and PyDriller's
per-commit diff parsing would be ~10-50x slower for no benefit here across a
26+ repo portfolio. Modules that need diffs (ontology, escape) use PyDriller.

Metrics, defined precisely so they can be recomputed by hand from git log:

- tier: by days since last commit -- active <=90, recent <=365, aging <=1095,
  dormant >1095. Same thresholds used in the Button/Chronicle engagement.
- bus_factor_gini: Gini coefficient of each author's share of commits in this
  repo. G = (2 * sum(i * x_i) / (n * sum(x_i))) - (n+1)/n, x_i = each
  author's commit count sorted ascending, i = 1-indexed rank. G=0 is perfectly
  even authorship; G->1 is one author owns everything.
- top_author_share: the single largest author's commit count / total commits.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from .util import run, write_csv

FIELD_SEP = "\x1f"
LOG_FORMAT = FIELD_SEP.join(["%H", "%ae", "%ad", "%P"])


@dataclass
class RepoInventory:
    repo: str
    total_commits: int
    merge_commits: int
    unique_authors: int
    first_commit: str
    last_commit: str
    tenure_days: int
    days_since_last_commit: int
    tier: str
    commits_last_90d: int
    commits_prior_90d: int
    bus_factor_gini: float
    top_author_share: float
    top_author: str


def _tier(days_since_last: int) -> str:
    if days_since_last <= 90:
        return "active"
    if days_since_last <= 365:
        return "recent"
    if days_since_last <= 1095:
        return "aging"
    return "dormant"


def _gini(counts: list[int]) -> float:
    if not counts or sum(counts) == 0:
        return 0.0
    xs = sorted(counts)
    n = len(xs)
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 4)


def analyze_repo(repo: Path, now: datetime | None = None) -> RepoInventory:
    now = now or datetime.now(timezone.utc)
    res = run(["git", "log", "--all", "--no-renames", f"--format={LOG_FORMAT}",
               "--date=iso-strict"], cwd=repo)
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    if not lines:
        raise ValueError(f"{repo} has zero commits on any ref -- not a usable repo")

    authors: dict[str, int] = {}
    dates: list[datetime] = []
    merges = 0
    for line in lines:
        parts = line.split(FIELD_SEP)
        _h, author, date_s, parents = parts[0], parts[1], parts[2], parts[3]
        authors[author] = authors.get(author, 0) + 1
        dates.append(datetime.fromisoformat(date_s))
        if len(parents.split()) > 1:
            merges += 1

    dates.sort()
    first, last = dates[0], dates[-1]
    days_since_last = (now - last).days
    tenure_days = (last - first).days
    cutoff_90 = now.timestamp() - 90 * 86400
    cutoff_180 = now.timestamp() - 180 * 86400
    commits_last_90 = sum(1 for d in dates if d.timestamp() >= cutoff_90)
    commits_prior_90 = sum(1 for d in dates if cutoff_180 <= d.timestamp() < cutoff_90)

    top_author, top_count = max(authors.items(), key=lambda kv: kv[1])

    return RepoInventory(
        repo=repo.name,
        total_commits=len(lines),
        merge_commits=merges,
        unique_authors=len(authors),
        first_commit=first.date().isoformat(),
        last_commit=last.date().isoformat(),
        tenure_days=tenure_days,
        days_since_last_commit=days_since_last,
        tier=_tier(days_since_last),
        commits_last_90d=commits_last_90,
        commits_prior_90d=commits_prior_90,
        bus_factor_gini=_gini(list(authors.values())),
        top_author_share=round(top_count / len(lines), 4),
        top_author=top_author,
    )


def run_inventory(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    rows.sort(key=lambda r: -r["total_commits"])
    out_path = out_dir / "inventory.csv"
    write_csv(out_path, rows)
    return out_path
