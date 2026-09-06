"""Tooling/config drift *within* one repo's tree: the same dependency name
pinned to different version strings across sibling manifests, and lint/
format config divergence between manifests' own directories.

Two independent drift dimensions, each its own `config_kind`:

- `"dependency_version"`: see dependency_versions.py (parsing) and
  dependency_drift.py (comparison).
- `"eslint"` / `"ruff"` / `"golangci"`: see lint_configs.py (per-manifest
  fingerprinting) and lint_drift.py (comparison).

**Column semantics note** -- `packages_compared`/`packages_with_drift` are
reused across both dimensions but count different *kinds* of thing,
documented here so a report reader isn't misled by the shared column
name: for `config_kind="dependency_version"` they count DEPENDENCY NAMES
(how many distinct package names were shared across >=2 manifests, and
how many of those had divergent versions); for `"eslint"`/`"ruff"`/
`"golangci"` they count MANIFEST-OWNING DIRECTORIES/FILES (how many
sibling locations were compared, and how many disagreed with the
majority state).

Split by concern across this package's submodules -- see each one's own
docstring for what it covers; `analyze.py` has the full row-shape writeup
for how the two dimensions combine into one repo's rows.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import ToolingDriftRow
from .runner import run_tooling_drift

__all__ = ["ToolingDriftRow", "analyze_repo", "run_tooling_drift"]
