"""Cross-repo (portfolio-wide) dependency-version discovery -- gathers each
repo's ROOT-level manifest (package.json / go.mod) and parses its pinned
dependency versions, one ecosystem at a time, for
cross_repo_dependency_drift.py to compare across the whole portfolio.

**Root-only scope, same call as cross_repo_lint.py**: a portfolio-wide
"does this dependency name drift across the fleet" question is about each
repo's own top-level dependency set, not every nested `packages/*`
manifest discovery.py's full-tree walk finds inside a monorepo -- that
within-repo drift is already dependency_version_check.py's job. Pulling
nested manifests in here would double-count the same drift under a
different label, the exact trap cross_repo_lint.py's own docstring calls
out for lint configs.

Reuses `root_manifest` from cross_repo_lint.py unchanged (format-agnostic:
"does repo X have a root file named Y" applies identically to a
dependency manifest as to a lint config's owning manifest) -- only the
*parsing* is new wiring, via dependency_versions.py's existing
`package_json_deps`/`go_mod_requires`, never a new parser.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from .cross_repo_lint import root_manifest
from .dependency_versions import go_mod_requires, package_json_deps

# ecosystem label -> (root manifest filename, parser). Mirrors
# LINT_KIND_SPECS's shape in lint_drift.py: one registry ties each
# ecosystem to its own filename and parse function, so adding an
# ecosystem later is one new tuple, not a new branch anywhere else.
DEPENDENCY_ECOSYSTEM_SPECS: tuple[tuple[str, str, Callable[[Path], dict[str, str]]], ...] = (
    ("package.json", "package.json", package_json_deps),
    ("go.mod", "go.mod", go_mod_requires),
)


def portfolio_root_deps(
    repos: list[Path], filename: str, parse_fn: Callable[[Path], dict[str, str]]
) -> dict[Path, dict[str, str]]:
    """manifest path -> {dep_name: version}, for every repo in `repos`
    that has a root-level `filename` manifest -- a repo with none at its
    root simply contributes no entry, the same "absent, not a
    zero-dependency vote" shape as cross_repo_lint.py's
    `canonical_fingerprints`."""
    result: dict[Path, dict[str, str]] = {}
    for repo in repos:
        manifest = root_manifest(repo, filename)
        if manifest is not None:
            result[manifest] = parse_fn(manifest)
    return result


def group_by_name(portfolio_deps: dict[Path, dict[str, str]]) -> dict[str, dict[str, list[str]]]:
    """dependency name -> version -> sorted repo names pinning that
    version, derived from each manifest's own parent directory name (the
    same `repo.name` convention every other row in this package uses).
    This is the one piece dependency_drift.py's generic comparison
    deliberately doesn't return (it only counts names/versions, staying
    format- and repo-agnostic) -- see cross_repo_dependency_drift.py's
    docstring for why this dimension's row shape needs it."""
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for manifest_path, deps in portfolio_deps.items():
        repo_name = manifest_path.parent.name
        for name, version in deps.items():
            grouped[name][version].append(repo_name)
    for versions in grouped.values():
        for repo_names in versions.values():
            repo_names.sort()
    return grouped
