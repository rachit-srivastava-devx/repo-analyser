"""Pure bucketing helpers for commit_activity.py. Full formulas and the
methodology are in docs/METHODOLOGY.md ("inventory.py -- repo tiering &
activity"); kept here only as much as needed to read the code itself.
"""
from __future__ import annotations


def _tier(days_since_last: int) -> str:
    if days_since_last <= 90:
        return "active"
    if days_since_last <= 365:
        return "recent"
    if days_since_last <= 1095:
        return "aging"
    return "dormant"


def _gini(counts: list[int]) -> float:
    """Gini coefficient of each author's share of commits: G=0 is perfectly
    even authorship, G->1 is one author owns everything."""
    if not counts or sum(counts) == 0:
        return 0.0
    xs = sorted(counts)
    n = len(xs)
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 4)
