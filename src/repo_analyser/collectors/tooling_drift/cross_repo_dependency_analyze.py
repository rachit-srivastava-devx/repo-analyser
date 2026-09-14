"""Portfolio-wide orchestration for the cross-repo dependency-version
drift dimension: runs `check_cross_repo_dependency_drift` once per
ecosystem in `DEPENDENCY_ECOSYSTEM_SPECS` (package.json, go.mod --
pyproject.toml/Cargo.toml are never version-compared anywhere in this
package, see dependency_versions.py), mirroring how cross_repo_analyze.py
drives the lint dimension off `LINT_KIND_SPECS`.

Returns rows for the SEPARATE `tooling_drift_cross_repo_deps.csv`
artifact (see cross_repo_dependency_drift.py's row-shape decision) plus
one portfolio summary per ecosystem for tooling_drift_summary.json's
"cross_repo_dependency_versions" section.
"""
from __future__ import annotations

from pathlib import Path

from .cross_repo_dependency_drift import check_cross_repo_dependency_drift
from .cross_repo_dependency_versions import DEPENDENCY_ECOSYSTEM_SPECS
from .models import CrossRepoDependencyRow, CrossRepoDependencySummary


def run_cross_repo_dependency_drift(
    repos: list[Path],
) -> tuple[list[CrossRepoDependencyRow], list[CrossRepoDependencySummary]]:
    """Runs once per portfolio (not per-repo): one (rows, summary) result
    per ecosystem in `DEPENDENCY_ECOSYSTEM_SPECS`. `repos` is the full
    portfolio list exactly as passed into `run_tooling_drift` --
    de-duplication and the single-repo-portfolio skip are
    `check_cross_repo_dependency_drift`'s own responsibility, not this
    function's."""
    all_rows: list[CrossRepoDependencyRow] = []
    summaries: list[CrossRepoDependencySummary] = []
    for ecosystem, filename, parse_fn in DEPENDENCY_ECOSYSTEM_SPECS:
        rows, summary = check_cross_repo_dependency_drift(repos, ecosystem, filename, parse_fn)
        all_rows.extend(rows)
        summaries.append(summary)
    return all_rows, summaries
