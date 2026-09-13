"""Per-repo orchestration: precondition checks, then hand off to
aggregate.collect for the actual scan+blame+rollup, then shape the result.

`skip_reason` is populated only for a genuine precondition failure -- the
given path doesn't exist, or isn't a git repository at all -- same
`is_git_repo`-gated pattern as codebase_modularity/analyze.py. An empty
repo, or a repo with zero markers, is a real (non-skipped) all-zero
result: every repo has *some* tracked-file content to check, so finding
nothing is a finding, not a precondition failure.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ...core.util import is_git_repo
from .aggregate import STALE_MARKER_AGE_DAYS, collect
from .models import DebtMarkersResult


def _skipped(repo: Path, reason: str) -> DebtMarkersResult:
    return DebtMarkersResult(
        repo=repo.name, total_marker_count=0, marker_counts_by_type="",
        average_age_days=0.0, oldest_marker_age_days=0, oldest_marker_location="",
        stale_marker_count=0, skip_reason=reason,
    )


def analyze_repo(repo: Path, now: datetime | None = None) -> DebtMarkersResult:
    if not repo.exists():
        return _skipped(repo, f"{repo}: path does not exist")
    if not is_git_repo(repo):
        return _skipped(repo, f"{repo}: not a git repository (no .git file or directory)")

    now = now or datetime.now(timezone.utc)
    agg = collect(repo, int(now.timestamp()))

    total = sum(agg.by_type.values())
    return DebtMarkersResult(
        repo=repo.name,
        total_marker_count=total,
        marker_counts_by_type=";".join(f"{t}:{c}" for t, c in sorted(agg.by_type.items())),
        average_age_days=round(sum(agg.ages) / len(agg.ages), 1) if agg.ages else 0.0,
        oldest_marker_age_days=agg.oldest_age or 0,
        oldest_marker_location=agg.oldest_location,
        stale_marker_count=sum(1 for age in agg.ages if age > STALE_MARKER_AGE_DAYS),
        skip_reason="",
    )
