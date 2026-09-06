"""Per-repo "dependency_version" row: merges the JS (package.json) and Go
(go.mod) dependency-version comparisons (see dependency_drift.py) into at
most ONE row per repo -- never compared across formats ("requests" in a
pyproject.toml and "requests" in a package.json are not the same package
just because the string matches). A repo drifting in both ecosystems at
once still gets a single "dependency_version" row with both ecosystems'
pkg@version pairs in `drift_detail`, since a repo can only have one row
per (repo, config_kind) pair.
"""
from __future__ import annotations

from pathlib import Path

from .dependency_drift import dependency_drift
from .dependency_versions import go_mod_requires, package_json_deps
from .models import MIN_MANIFESTS_TO_COMPARE, ToolingDriftRow


def check_dependency_version_drift(
    repo: Path, manifests: dict[str, list[Path]]
) -> tuple[ToolingDriftRow | None, bool, list[str]]:
    """Returns (row-or-None, attempted, shortfall-messages). `attempted`
    is True the moment EITHER ecosystem had enough manifests to compare
    -- it only stays False when NEITHER package.json NOR go.mod reached
    `MIN_MANIFESTS_TO_COMPARE` anywhere in the tree."""
    attempted = False
    packages_compared = 0
    packages_with_drift = 0
    detail: list[str] = []
    shortfalls: list[str] = []

    pkg_paths = manifests["package.json"]
    if len(pkg_paths) >= MIN_MANIFESTS_TO_COMPARE:
        attempted = True
        c, d, det = dependency_drift({p: package_json_deps(p) for p in pkg_paths})
        packages_compared += c
        packages_with_drift += d
        detail.extend(det)
    else:
        shortfalls.append(f"dependency_version (package.json): only {len(pkg_paths)} found, need >=2")

    go_paths = manifests["go.mod"]
    if len(go_paths) >= MIN_MANIFESTS_TO_COMPARE:
        attempted = True
        c, d, det = dependency_drift({p: go_mod_requires(p) for p in go_paths})
        packages_compared += c
        packages_with_drift += d
        detail.extend(det)
    else:
        shortfalls.append(f"dependency_version (go.mod): only {len(go_paths)} found, need >=2")

    if not attempted or packages_with_drift == 0:
        return None, attempted, shortfalls
    return (
        ToolingDriftRow(
            repo=repo.name, config_kind="dependency_version",
            packages_compared=packages_compared, packages_with_drift=packages_with_drift,
            drift_detail=";".join(detail), skip_reason="",
        ),
        attempted, shortfalls,
    )
