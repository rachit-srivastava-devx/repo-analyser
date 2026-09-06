"""Manifest discovery -- one full-tree walk, bucketed by filename.

**Traversal shape -- a deliberate, called-out exception, not an oversight**
(see docs/ROADMAP.md's tooling_drift.py bullet): every other collector in
this package reads at most one manifest per repo root. This module instead
walks the FULL repo tree for every package.json / pyproject.toml / go.mod /
Cargo.toml anywhere under the root (respecting core.lang.EXCLUDE_DIR_PARTS,
same filter convention as repo_type.py's `_tracked_files`) -- because drift
is a property of TWO OR MORE manifests of the same kind existing side by
side (an unmanaged monorepo's per-package manifests, most commonly), which
by definition can't be observed from a single repo-root manifest. Most
relevant once repo_type.py flags `primary_type=monorepo`, but this module
doesn't gate on that -- an ad hoc `packages/*` layout with no workspace
marker file still has real drift worth reporting.

**Cargo.toml is discovered** (it still counts toward "how many manifests
exist anywhere in the tree") **but is never content-compared** -- see
dependency_versions.py and lint_configs.py for the comparisons that do
exist: extracting Cargo.toml's `[dependencies]` table honestly needs real
TOML array/table parsing, which this module (like repo_type.py before it)
deliberately avoids adding as a new dependency.
"""
from __future__ import annotations

from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from .models import MANIFEST_NAMES


def find_manifests(repo: Path) -> dict[str, list[Path]]:
    """Every package.json / pyproject.toml / go.mod / Cargo.toml anywhere
    under `repo`, bucketed by filename via ONE tree walk -- O(total files
    in the repo), the same cost class as repo_type.py's `_tracked_files`
    (which also does a single `rglob("*")` pass), not four separate
    walks. Respects `core.lang.EXCLUDE_DIR_PARTS` the same way
    `_tracked_files` does: filter by path parts after the walk, no
    per-directory fnmatch special-casing."""
    found: dict[str, list[Path]] = {name: [] for name in MANIFEST_NAMES}
    for p in repo.rglob("*"):
        if not p.is_file() or p.name not in found:
            continue
        if any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts):
            continue
        found[p.name].append(p)
    for paths in found.values():
        paths.sort()
    return found
