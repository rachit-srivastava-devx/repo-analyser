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
    config_kind: str  # "dependency_version" | "eslint" | "ruff" | "golangci" | "none"
    packages_compared: int
    packages_with_drift: int
    drift_detail: str
    skip_reason: str
