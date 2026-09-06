"""Per-repo orchestration: combines the dependency-version and lint-config
drift dimensions into `ToolingDriftRow`s.

**Row shape decision** (explicitly a judgment call this module's own brief
leaves open -- stated and justified here, not left implicit): one row per
(repo, config_kind) for each of the four real kinds (dependency_version,
eslint, ruff, golangci), but ONLY when that kind's comparison was actually
attempted (>=2 manifests of the relevant filename existed anywhere in the
tree) AND drift was found. A kind that was attempted and found NO drift
produces zero rows for that kind -- a clean, boring, legitimate
non-finding, matching every other collector's own "empty means genuinely
nothing" convention (deps_audit.py's CVE csv has the same shape: a repo
with no CVEs contributes zero rows, not a placeholder). The alternative
considered -- one row per config_kind per repo unconditionally (always 4
rows, including a permanent "0 found, need >=2" skip row for every kind a
repo's tech stack simply doesn't use, e.g. "golangci: 0 found" on every
non-Go repo forever) -- was rejected: it would drown every real finding in
identical, low-information rows repeated across nearly every
single-language repo in a portfolio, the opposite of what a report is for.

Instead, exactly ONE additional summary row per repo, with
`config_kind="none"` (deliberately outside the four real per-kind labels),
is emitted ONLY when NOT EVEN ONE of the four kinds could be attempted
anywhere in the tree (the common "this repo only has one manifest,
period" case docs/ROADMAP.md's own bullet calls out: "most single-
manifest repos will legitimately report this, a common non-error
result"). Invariant that follows from this: `skip_reason` is populated if
and only if `config_kind == "none"`.
"""
from __future__ import annotations

from pathlib import Path

from .dependency_version_check import check_dependency_version_drift
from .discovery import find_manifests
from .lint_drift import LINT_KIND_SPECS, check_lint_config_drift
from .models import MIN_MANIFESTS_TO_COMPARE, ToolingDriftRow


def analyze_repo(repo: Path) -> list[ToolingDriftRow]:
    manifests = find_manifests(repo)
    rows: list[ToolingDriftRow] = []
    attempted_any = False
    shortfalls: list[str] = []

    dep_row, dep_attempted, dep_shortfalls = check_dependency_version_drift(repo, manifests)
    attempted_any = attempted_any or dep_attempted
    shortfalls.extend(dep_shortfalls)
    if dep_row:
        rows.append(dep_row)

    for kind, filename, display_fn in LINT_KIND_SPECS:
        owning = manifests[filename]
        if len(owning) < MIN_MANIFESTS_TO_COMPARE:
            shortfalls.append(f"{kind} ({filename}): only {len(owning)} found, need >=2")
            continue
        attempted_any = True
        row = check_lint_config_drift(repo, owning, kind, display_fn)
        if row:
            rows.append(row)

    if not attempted_any:
        total = sum(len(v) for v in manifests.values())
        reason = (
            f"only {total} manifest(s) found across package.json/pyproject.toml/go.mod/Cargo.toml "
            "anywhere in the tree; every drift check needs >=2 manifests of the same kind to compare "
            "(" + "; ".join(shortfalls) + ")"
        )
        rows.append(ToolingDriftRow(
            repo=repo.name, config_kind="none", packages_compared=0, packages_with_drift=0,
            drift_detail="", skip_reason=reason,
        ))
    return rows
