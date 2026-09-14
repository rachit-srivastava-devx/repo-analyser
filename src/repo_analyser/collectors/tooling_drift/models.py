"""Data shape and constants shared across tooling_drift's submodules."""
from __future__ import annotations

from dataclasses import dataclass

MANIFEST_NAMES = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml")

# Below this many manifests of the same filename anywhere in the tree, a
# drift comparison is meaningless by definition -- there is nothing to
# compare a single manifest *against*. Named so the threshold is stated
# once, not a magic "2" scattered through the comparison functions.
MIN_MANIFESTS_TO_COMPARE = 2

ESLINT_CONFIG_NAMES = (".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
                        ".eslintrc.yml", ".eslintrc.yaml")
GOLANGCI_CONFIG_NAMES = (".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json")


@dataclass
class ToolingDriftRow:
    repo: str
    # "dependency_version" | "eslint" | "ruff" | "golangci" (within-repo) |
    # "cross_repo_eslint" | "cross_repo_ruff" | "cross_repo_golangci"
    # (portfolio-wide, see cross_repo_drift.py) | "none"
    config_kind: str
    packages_compared: int
    packages_with_drift: int
    drift_detail: str
    skip_reason: str


@dataclass
class CrossRepoKindSummary:
    """One lint kind's portfolio-wide canonical-config finding, independent
    of whether any repo actually drifted -- written into
    tooling_drift_summary.json's "cross_repo_canonical" section (see
    runner.py) so a reader can see the canonical fingerprint and how many
    repos it was computed from even when `skipped_reason` is empty and
    zero repos drifted (the common "everyone already agrees" case)."""
    config_kind: str
    canonical_fingerprint: str | None
    repos_compared: int
    repos_drifted: int
    skipped_reason: str


@dataclass
class CrossRepoDependencyRow:
    """One drifted dependency NAME's portfolio-wide finding for one
    ecosystem -- deliberately NOT a `ToolingDriftRow` (see
    cross_repo_dependency_drift.py's "Row shape decision"): this
    dimension's natural grain is the dependency name, which spans
    multiple repos, not one repo's own row. Written to the separate
    tooling_drift_cross_repo_deps.csv artifact, never mixed into
    tooling_drift.csv's per-repo rows."""
    dependency_name: str
    ecosystem: str  # "package.json" | "go.mod"
    versions_found: str  # sorted, ";"-joined distinct version strings
    repos_by_version: str  # "version:repoA,repoB;version2:repoC" -- one group per version
    repo_count: int  # total repos (summed across every version) pinning this dependency


@dataclass
class CrossRepoDependencySummary:
    """One ecosystem's portfolio-wide dependency-version comparison,
    written into tooling_drift_summary.json's
    "cross_repo_dependency_versions" section -- populated even when zero
    dependencies drifted (the common "fleet already agrees" case),
    mirroring `CrossRepoKindSummary`'s always-present-even-when-clean
    convention above."""
    ecosystem: str
    repos_compared: int
    dependencies_compared: int
    dependencies_drifted: int
    skipped_reason: str
