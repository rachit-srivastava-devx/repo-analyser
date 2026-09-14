"""Cross-repo majority/canonical-config computation: given one lint kind's
per-repo root-manifest fingerprints (cross_repo_lint.py), decides which
fingerprint is "canonical" for the portfolio and builds a `ToolingDriftRow`
for every repo that disagrees with it.

**"missing" participates in the vote** -- a repo whose root manifest exists
but declares no config for this tool (`display_fn` returns "missing") is
just another fingerprint value, same as lint_drift.py's
`check_lint_config_drift` treats it within one repo. "Missing" can
therefore legitimately BE the canonical fingerprint -- "most repos in this
portfolio don't even configure ruff" is a real finding, not a case to hide
by excluding "missing" repos from the count. (A repo with no root manifest
AT ALL is a different, earlier exclusion, in cross_repo_lint.py.)

**Tie-break** -- `Counter.most_common()` is not deterministic on ties (it
depends on dict/repo insertion order), so ties are broken explicitly by
lexicographically smallest fingerprint string via
`sorted(..., key=(-count, fingerprint))`.

**Duplicates and single-repo portfolios** -- repos are de-duplicated by
resolved real path first (cross_repo_lint.py's `dedupe_by_real_path`), so
a symlink alias can't out-vote distinct repos; a portfolio (or a kind's
own population within it) under `MIN_MANIFESTS_TO_COMPARE` is skipped
entirely -- no "majority" exists at sample size 1.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path

from .cross_repo_lint import canonical_fingerprints, dedupe_by_real_path
from .models import MIN_MANIFESTS_TO_COMPARE, CrossRepoKindSummary, ToolingDriftRow


def _canonical_fingerprint(displays: dict[Path, str]) -> str:
    counts = Counter(displays.values())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[0][0]


def check_cross_repo_lint_drift(
    repos: list[Path], config_kind: str, filename: str, display_fn: Callable[[Path], str]
) -> tuple[list[ToolingDriftRow], CrossRepoKindSummary]:
    """Returns (rows-for-drifted-repos, portfolio-wide summary). Empty rows
    plus a populated `skipped_reason` when the portfolio (or this kind's
    population within it) is too small to compare; empty rows with
    `skipped_reason == ""` means the comparison ran and found every repo
    already agreeing -- a clean, legitimate non-finding."""
    unique_repos = dedupe_by_real_path(repos)
    if len(unique_repos) < MIN_MANIFESTS_TO_COMPARE:
        return [], CrossRepoKindSummary(
            config_kind=config_kind, canonical_fingerprint=None, repos_compared=0, repos_drifted=0,
            skipped_reason=f"portfolio has {len(unique_repos)} distinct repo(s), need >=2 to have a canonical config",
        )

    displays = canonical_fingerprints(unique_repos, filename, display_fn)
    if len(displays) < MIN_MANIFESTS_TO_COMPARE:
        return [], CrossRepoKindSummary(
            config_kind=config_kind, canonical_fingerprint=None, repos_compared=len(displays), repos_drifted=0,
            skipped_reason=f"only {len(displays)} repo(s) have a root {filename}, need >=2 to compare",
        )

    canonical = _canonical_fingerprint(displays)
    drifted = {repo: fp for repo, fp in displays.items() if fp != canonical}
    detail = ";".join(f"{r.name}:{fp}" for r, fp in sorted(displays.items(), key=lambda kv: kv[0].name))
    rows = [
        ToolingDriftRow(
            repo=repo.name, config_kind=config_kind, packages_compared=len(displays),
            packages_with_drift=len(drifted), drift_detail=detail, skip_reason="",
        )
        for repo in sorted(drifted, key=lambda r: r.name)
    ]
    summary = CrossRepoKindSummary(
        config_kind=config_kind, canonical_fingerprint=canonical,
        repos_compared=len(displays), repos_drifted=len(drifted), skipped_reason="",
    )
    return rows, summary
