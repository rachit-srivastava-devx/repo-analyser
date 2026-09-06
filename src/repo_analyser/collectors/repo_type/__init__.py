"""Repo-type detection: which archetype(s) this repo matches, per
docs/checklist-by-repo-type/detecting-repo-type.md's full signal table (15
original signals + 13 newer-archetype signals) -- so a per-repo digest can
say which checklist actually applies, and a portfolio-wide run can group
repos by shape before applying type-specific criteria.

Two independent axes, computed the same way for every repo -- `primary_type`
(single_repo/monorepo/polyrepo/microservices/meta_repo, mutually exclusive,
checked in the doc's own listed order) and `content_types` (zero or more of
16 content-purpose archetypes, independent of primary_type and each other).
See each submodule's own docstring for which piece of the split it covers;
primary_signals.py/primary_type.py have the full primary-axis writeup and
content_dev_docs.py has the full content-axis writeup.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .constants import POLYREPO_FLEET_MIN_SIZE, SERVICE_MESH_CRD_KINDS
from .models import RepoTypeResult
from .runner import run_repo_type

__all__ = [
    "POLYREPO_FLEET_MIN_SIZE",
    "RepoTypeResult",
    "SERVICE_MESH_CRD_KINDS",
    "analyze_repo",
    "run_repo_type",
]
