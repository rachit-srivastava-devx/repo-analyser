"""The RepoInventory row shape -- one row per repo, written to inventory.csv
by runner.py. See commit_activity.py, changelog.py, and staleness_band.py for
where each field's value is actually computed."""
from __future__ import annotations

from dataclasses import dataclass


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
    staleness_band: str | None
    changelog_present: bool
    changelog_last_entry_date: str | None
    latest_tag_date: str | None
    changelog_staleness_days: int | None
