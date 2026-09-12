"""Per-repo orchestration: combines module_size.py, god_class.py, and
layering.py's three independent signals into one CodebaseModularityResult.
See package docstring for the full contract.

Unlike migration_hygiene, this collector has no "no convention found"
case in the normal sense -- every repo has *some* files, so an all-zero
result for a genuinely small/empty repo is a real finding, not a skip.
`skip_reason` is populated only for a genuine precondition failure: the
given path doesn't exist, or isn't a git repository at all (checked via
core.util.is_git_repo, same helper every other collector's skip path
uses)."""
from __future__ import annotations

from pathlib import Path

from ...core.util import is_git_repo
from .god_class import find_god_class_findings
from .layering import find_layering_findings
from .models import CodebaseModularityResult
from .module_size import find_module_size_findings


def _skipped(repo: Path, reason: str) -> CodebaseModularityResult:
    return CodebaseModularityResult(
        repo=repo.name,
        oversized_file_count=0, oversized_files="",
        oversized_package_count=0, oversized_packages="",
        god_class_count=0, god_classes="", god_class_language_supported=False,
        layering_tool_detected="", layering_config_path="",
        skip_reason=reason,
    )


def analyze_repo(repo: Path) -> CodebaseModularityResult:
    if not repo.exists():
        return _skipped(repo, f"{repo}: path does not exist")
    if not is_git_repo(repo):
        return _skipped(repo, f"{repo}: not a git repository (no .git file or directory)")

    module_size = find_module_size_findings(repo)
    god_class = find_god_class_findings(repo)
    layering = find_layering_findings(repo)

    return CodebaseModularityResult(
        repo=repo.name,
        oversized_file_count=module_size.oversized_file_count,
        oversized_files=module_size.oversized_files,
        oversized_package_count=module_size.oversized_package_count,
        oversized_packages=module_size.oversized_packages,
        god_class_count=god_class.god_class_count,
        god_classes=god_class.god_classes,
        god_class_language_supported=god_class.god_class_language_supported,
        layering_tool_detected=layering.layering_tool_detected,
        layering_config_path=layering.layering_config_path,
        skip_reason="",
    )
