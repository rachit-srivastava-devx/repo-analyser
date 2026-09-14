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
