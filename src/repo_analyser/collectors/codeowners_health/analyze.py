"""Per-repo CODEOWNERS coverage: locate the file, parse it, match its rules
against the tracked file tree with last-match-wins semantics, and reduce
that into the counts docs/checklist-by-repo-type/monorepo.md and
polyrepo.md's CODEOWNERS coverage/accuracy criteria ask for.
"""
from __future__ import annotations

from pathlib import Path

from .fileio import tracked_files
from .matcher import match_all
from .models import CodeownersHealthResult
from .parser import find_codeowners, parse_codeowners


def analyze_repo(repo: Path) -> CodeownersHealthResult:
    codeowners_path = find_codeowners(repo)
    rules = parse_codeowners(codeowners_path) if codeowners_path else []
    files = [str(p) for p in tracked_files(repo)]

    ownership, matched_rule_indices = match_all(rules, files)
    total = len(files)
    owned = len(ownership)
    coverage = round(owned / total * 100, 2) if total else 0.0
    distinct_owners = {owner for owners in ownership.values() for owner in owners}
    stale = sum(1 for index in range(len(rules)) if index not in matched_rule_indices)

    return CodeownersHealthResult(
        repo=repo.name,
        has_codeowners=codeowners_path is not None,
        codeowners_path=str(codeowners_path.relative_to(repo)) if codeowners_path else None,
        total_tracked_files=total,
        owned_file_count=owned,
        coverage_pct=coverage,
        unowned_file_count=total - owned,
        distinct_owners=len(distinct_owners),
        stale_rule_count=stale,
    )
