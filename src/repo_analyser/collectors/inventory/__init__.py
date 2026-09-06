"""Repo tiering, activity, and lifecycle-health signals: commit velocity,
tenure, bus factor, changelog discipline, and a portfolio-wide staleness
band. See each submodule's own docstring for which piece of the split it
covers -- commit_activity.py (+ tiering.py) has the original velocity/
tenure/bus-factor writeup, changelog.py the changelog-discipline signal
(docs/checklist-by-repo-type/single-repo.md), and staleness_band.py the
lifecycle-staleness bucketing (docs/checklist-by-repo-type/polyrepo.md).
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import RepoInventory
from .runner import run_inventory

__all__ = [
    "RepoInventory",
    "analyze_repo",
    "run_inventory",
]
