"""Commit velocity, tenure, and bus factor -- the original inventory signal.

Uses plain `git log` (not PyDriller): this needs only commit metadata
(hash/author/date/parents), not diffs, and PyDriller's per-commit diff
parsing would be far slower for no benefit here. See docs/METHODOLOGY.md for
the exact tier/Gini formulas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ...core.util import run
from .tiering import _gini, _tier

FIELD_SEP = "\x1f"
LOG_FORMAT = FIELD_SEP.join(["%H", "%ae", "%ad", "%P"])


@dataclass
class CommitActivity:
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


def collect_commit_activity(repo: Path, now: datetime) -> CommitActivity:
    res = run(["git", "log", "--all", "--no-renames", f"--format={LOG_FORMAT}",
               "--date=iso-strict"], cwd=repo)
    lines = [line for line in res.stdout.splitlines() if line.strip()]
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

    return CommitActivity(
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
