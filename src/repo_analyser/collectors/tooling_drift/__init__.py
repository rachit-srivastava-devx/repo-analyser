"""Tooling/config drift *within* one repo's tree, and *across* repos in a
portfolio: the same dependency name pinned to different version strings
across sibling manifests (within one repo, or across a whole portfolio's
root manifests), lint/format config divergence between manifests' own
directories, and (portfolio-wide) a repo's root-level lint/format config
forking from the portfolio's own canonical one.

Four independent drift dimensions:

- `"dependency_version"` (within one repo's tree, `ToolingDriftRow`): see
  dependency_versions.py (parsing) and dependency_drift.py (comparison).
- `"eslint"` / `"ruff"` / `"golangci"` (within one repo's tree,
  `ToolingDriftRow`): see lint_configs.py (per-manifest fingerprinting)
  and lint_drift.py (comparison).
- `"cross_repo_eslint"` / `"cross_repo_ruff"` / `"cross_repo_golangci"`
  (across a portfolio's repos, `ToolingDriftRow` in tooling_drift.csv):
  see cross_repo_lint.py (root-manifest fingerprinting, reusing
  lint_configs.py's same functions) and cross_repo_drift.py
  (majority/canonical comparison), orchestrated by cross_repo_analyze.py.
- Cross-repo dependency-version drift (across a portfolio's *root*
  manifests, package.json and go.mod): NOT a `ToolingDriftRow` -- one row
  per drifted DEPENDENCY NAME in the separate
  tooling_drift_cross_repo_deps.csv artifact, since a drifted dependency
  name spans multiple repos at once rather than being "one repo's"
  finding. See cross_repo_dependency_drift.py's own docstring for the
  full row-shape writeup and cross_repo_dependency_versions.py for the
  root-manifest gathering, orchestrated by
  cross_repo_dependency_analyze.py.

**Column semantics note** -- `packages_compared`/`packages_with_drift` are
reused across the three `ToolingDriftRow` dimensions but count different
*kinds* of thing, documented here so a report reader isn't misled by the
shared column name: for `config_kind="dependency_version"` they count
DEPENDENCY NAMES (how many distinct package names were shared across >=2
manifests, and how many of those had divergent versions); for
`"eslint"`/`"ruff"`/`"golangci"` they count MANIFEST-OWNING
DIRECTORIES/FILES (how many sibling locations were compared, and how many
disagreed with the majority state); for the `"cross_repo_*"` lint kinds
they count REPOS (how many portfolio repos had a root manifest of that
kind to compare, and how many of those disagreed with the portfolio's
canonical fingerprint). The cross-repo dependency-version dimension is a
separate CSV with its own, differently-named columns (`repo_count`, not
`packages_compared`) precisely so it never has to be shoehorned into this
already-overloaded column pair -- see cross_repo_dependency_drift.py.

Split by concern across this package's submodules -- see each one's own
docstring for what it covers; `analyze.py` has the full row-shape writeup
for how the within-repo dimensions combine into one repo's rows,
cross_repo_drift.py has the equivalent writeup for the portfolio-wide
lint dimension, and cross_repo_dependency_drift.py has the equivalent
writeup for the portfolio-wide dependency-version dimension.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import ToolingDriftRow
from .runner import run_tooling_drift

__all__ = ["ToolingDriftRow", "analyze_repo", "run_tooling_drift"]
