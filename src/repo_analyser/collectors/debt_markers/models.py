"""Result dataclass for the debt_markers collector. See package docstring
(__init__.py) for the full contract; marker_counts_by_type follows
flag_debt/models.py's semicolon-joined CSV-friendly-field convention."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DebtMarkersResult:
    repo: str
    total_marker_count: int
    marker_counts_by_type: str
    average_age_days: float
    oldest_marker_age_days: int
    oldest_marker_location: str
    stale_marker_count: int
    skip_reason: str
