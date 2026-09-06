"""Result shape for the codeowners_health collector: one row per repo,
covering CODEOWNERS presence, how much of the tracked file tree its rules
cover, and how many of its own rules are dead. See
docs/checklist-by-repo-type/monorepo.md and polyrepo.md's CODEOWNERS
coverage/accuracy criteria for the source of this shape.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CodeownersHealthResult:
    repo: str
    has_codeowners: bool
    codeowners_path: str | None
    total_tracked_files: int
    owned_file_count: int
    coverage_pct: float
    unowned_file_count: int
    distinct_owners: int
    stale_rule_count: int
