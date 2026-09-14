"""Portfolio-wide dependency-version drift comparison -- decides, per
ecosystem, which dependency NAMES disagree on pinned version across the
portfolio's root manifests. One row per DRIFTED DEPENDENCY NAME, not per
repo.

**Row shape decision** (this package's "state it and justify it"
convention -- see analyze.py's and cross_repo_drift.py's own writeups as
the models): a drifted dependency name SPANS multiple repos at once
(e.g. "requests" pinned to 2.28.0 in some repos, 2.31.0 in others) --
unlike a lint-config fork, not naturally "one repo's" finding. Forcing it
into `ToolingDriftRow` would either drop which OTHER repos disagree (one
row, one repo picked arbitrarily) or explode row count ((repo,
dependency) pairs). Decision: a SEPARATE CSV artifact
(tooling_drift_cross_repo_deps.csv, see runner.py), because
`ToolingDriftRow.repo` means "this row is about this repo" for every
other config_kind (`__init__.py`'s column-semantics note) -- a sentinel
or arbitrary `repo` value is the "alphabetical-by-accident" quiet
inconsistency AGENTS.md SS6 warns about, and SS4 sanctions a new artifact
for a genuinely different row grain. Portfolio-level view still surfaces
in tooling_drift_summary.json's new "cross_repo_dependency_versions"
section, mirroring "cross_repo_canonical" for the lint dimension.

**No row-count cap** -- a large portfolio with many shared dependencies
can legitimately produce many rows. Reported in full, never sampled:
hiding "verbose but true" findings is the silently-wrong-result failure
mode ADR-0001 forbids; filter the CSV by `repo_count` if that's too much.

Reuses `dependency_drift()` UNCHANGED for the authoritative name-level
compared/drifted counts; only adds the per-repo-per-version GROUPING that
function deliberately doesn't return (`group_by_name`).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .cross_repo_dependency_versions import group_by_name, portfolio_root_deps
from .cross_repo_lint import dedupe_by_real_path
from .dependency_drift import dependency_drift
from .models import MIN_MANIFESTS_TO_COMPARE, CrossRepoDependencyRow, CrossRepoDependencySummary


def check_cross_repo_dependency_drift(
    repos: list[Path], ecosystem: str, filename: str, parse_fn: Callable[[Path], dict[str, str]]
) -> tuple[list[CrossRepoDependencyRow], CrossRepoDependencySummary]:
    """Returns (rows-for-drifted-dependency-names, portfolio-wide
    summary). Empty rows plus a populated `skipped_reason` when the
    portfolio (or this ecosystem's root-manifest population within it) is
    too small to compare; empty rows with `skipped_reason == ""` means
    the comparison ran and every shared dependency name already agrees --
    a clean, legitimate non-finding."""
    unique_repos = dedupe_by_real_path(repos)
    if len(unique_repos) < MIN_MANIFESTS_TO_COMPARE:
        return [], CrossRepoDependencySummary(
            ecosystem=ecosystem, repos_compared=0, dependencies_compared=0, dependencies_drifted=0,
            skipped_reason=f"portfolio has {len(unique_repos)} distinct repo(s), need >=2 to compare dependencies",
        )

    portfolio_deps = portfolio_root_deps(unique_repos, filename, parse_fn)
    if len(portfolio_deps) < MIN_MANIFESTS_TO_COMPARE:
        return [], CrossRepoDependencySummary(
            ecosystem=ecosystem, repos_compared=len(portfolio_deps), dependencies_compared=0, dependencies_drifted=0,
            skipped_reason=f"only {len(portfolio_deps)} repo(s) have a root {filename}, need >=2 to compare",
        )

    compared, drifted, _ = dependency_drift(portfolio_deps)
    grouped = group_by_name(portfolio_deps)
    rows: list[CrossRepoDependencyRow] = []
    for name in sorted(grouped):
        versions = grouped[name]
        repo_count = sum(len(repo_names) for repo_names in versions.values())
        if repo_count < MIN_MANIFESTS_TO_COMPARE or len(versions) <= 1:
            continue  # declared in <2 repos, or every repo already agrees -- not drift.
        versions_found = sorted(versions)
        rows.append(CrossRepoDependencyRow(
            dependency_name=name, ecosystem=ecosystem,
            versions_found=";".join(versions_found),
            repos_by_version=";".join(f"{v}:{','.join(versions[v])}" for v in versions_found),
            repo_count=repo_count,
        ))

    summary = CrossRepoDependencySummary(
        ecosystem=ecosystem, repos_compared=len(portfolio_deps),
        dependencies_compared=compared, dependencies_drifted=drifted, skipped_reason="",
    )
    return rows, summary
