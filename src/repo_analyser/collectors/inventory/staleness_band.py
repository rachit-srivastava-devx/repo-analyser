"""Portfolio-wide repo lifecycle staleness banding (docs/checklist-by-
repo-type/polyrepo.md, "Staleness/abandonment detection"): a coarse,
fixed-threshold bucket on top of the existing per-repo `days_since_last_commit`
metric, so a fleet-wide view can count how many repos fall in each band
without every consumer re-deriving thresholds of its own.

Deliberately separate from commit_activity.tiering's `_tier` (active/recent/
aging/dormant at 90/365/1095 days) -- that field predates this one and is
already relied on elsewhere (per_repo_digest.py, deep_reports.py); this is a
second, independently-named view for this specific checklist item, not a
replacement for it.
"""
from __future__ import annotations


def staleness_band(days_since_last_commit: int | None) -> str | None:
    """fresh <30 days, aging 30-90, stale 91-365, abandoned >365 (the lower
    band owns each shared boundary, same convention as `_tier`). None in,
    None out -- a repo with no usable last-commit signal must not silently
    default into any band, which would misreport its freshness."""
    if days_since_last_commit is None:
        return None
    if days_since_last_commit < 30:
        return "fresh"
    if days_since_last_commit <= 90:
        return "aging"
    if days_since_last_commit <= 365:
        return "stale"
    return "abandoned"
