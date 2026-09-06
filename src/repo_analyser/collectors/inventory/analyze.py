"""Per-repo orchestration: combine commit-activity, changelog-discipline, and
staleness-band signals into one RepoInventory row."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .changelog import collect_changelog_signals
from .commit_activity import collect_commit_activity
from .models import RepoInventory
from .staleness_band import staleness_band


def analyze_repo(repo: Path, now: datetime | None = None) -> RepoInventory:
    now = now or datetime.now(timezone.utc)
    activity = collect_commit_activity(repo, now)
    changelog = collect_changelog_signals(repo)
    return RepoInventory(
        repo=repo.name,
        total_commits=activity.total_commits,
        merge_commits=activity.merge_commits,
        unique_authors=activity.unique_authors,
        first_commit=activity.first_commit,
        last_commit=activity.last_commit,
        tenure_days=activity.tenure_days,
        days_since_last_commit=activity.days_since_last_commit,
        tier=activity.tier,
        commits_last_90d=activity.commits_last_90d,
        commits_prior_90d=activity.commits_prior_90d,
        bus_factor_gini=activity.bus_factor_gini,
        top_author_share=activity.top_author_share,
        top_author=activity.top_author,
        staleness_band=staleness_band(activity.days_since_last_commit),
        changelog_present=changelog.changelog_present,
        changelog_last_entry_date=changelog.changelog_last_entry_date,
        latest_tag_date=changelog.latest_tag_date,
        changelog_staleness_days=changelog.changelog_staleness_days,
    )
