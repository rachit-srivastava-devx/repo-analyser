"""Tooling/config drift *within* one repo's tree, and *across* repos in a
portfolio: the same dependency name pinned to different version strings
across sibling manifests, lint/format config divergence between manifests'
own directories, and (portfolio-wide) a repo's root-level lint/format
config forking from the portfolio's own canonical one.

Three independent drift dimensions, each its own `config_kind`:

- `"dependency_version"`: see dependency_versions.py (parsing) and
  dependency_drift.py (comparison).
- `"eslint"` / `"ruff"` / `"golangci"` (within one repo's tree): see
  lint_configs.py (per-manifest fingerprinting) and lint_drift.py
  (comparison).
- `"cross_repo_eslint"` / `"cross_repo_ruff"` / `"cross_repo_golangci"`
  (across a portfolio's repos): see cross_repo_lint.py (root-manifest
  fingerprinting, reusing lint_configs.py's same functions) and
  cross_repo_drift.py (majority/canonical comparison), orchestrated by
  cross_repo_analyze.py.

**Column semantics note** -- `packages_compared`/`packages_with_drift` are
reused across all three dimensions but count different *kinds* of thing,
documented here so a report reader isn't misled by the shared column
name: for `config_kind="dependency_version"` they count DEPENDENCY NAMES
(how many distinct package names were shared across >=2 manifests, and
how many of those had divergent versions); for `"eslint"`/`"ruff"`/
`"golangci"` they count MANIFEST-OWNING DIRECTORIES/FILES (how many
sibling locations were compared, and how many disagreed with the
majority state); for the `"cross_repo_*"` kinds they count REPOS (how
many portfolio repos had a root manifest of that kind to compare, and how
many of those disagreed with the portfolio's canonical fingerprint).

Split by concern across this package's submodules -- see each one's own
docstring for what it covers; `analyze.py` has the full row-shape writeup
for how the within-repo dimensions combine into one repo's rows, and
cross_repo_drift.py has the equivalent writeup for the portfolio-wide
dimension.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import ToolingDriftRow
from .runner import run_tooling_drift

__all__ = ["ToolingDriftRow", "analyze_repo", "run_tooling_drift"]
