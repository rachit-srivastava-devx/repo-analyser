"""Cross-repo (portfolio-wide) lint/format fingerprinting -- the "does this
repo's config match the portfolio's canonical one" dimension, as opposed to
lint_drift.py's within-one-repo "do this repo's own sibling manifests agree
with each other" dimension.

**Canonical-config scope decision**: "the repo's canonical config" here
means its REPO-ROOT-level manifest only (top-level package.json /
pyproject.toml / go.mod), never a manifest discovery.py's full-tree
`find_manifests` finds deeper inside a monorepo's subdirectories. A
portfolio-wide "does repo A fork from the portfolio's config" question is
about repo A's own top-level tooling identity -- the one thing every repo
in a polyrepo portfolio actually has one of -- not its internal monorepo
layout, which lint_drift.py already compares separately and which would
double-count the same drift under a different name if pulled in here too.

Reuses `eslint_display`/`ruff_display`/`golangci_display` from
lint_configs.py completely unchanged: the only difference from the
within-repo dimension is WHICH manifest path per repo gets fingerprinted
(exactly one, the root one, instead of every sibling manifest
discovery.py finds).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def dedupe_by_real_path(repos: list[Path]) -> list[Path]:
    """Collapses the same physical repo passed twice (e.g. a symlink
    alias) to a single entry, keyed by resolved real path -- so one repo
    can't out-vote genuinely distinct portfolio members in
    cross_repo_drift.py's majority computation just by being counted
    twice. Order of first appearance is preserved for determinism."""
    return list({r.resolve(): r for r in repos}.values())


def root_manifest(repo: Path, filename: str) -> Path | None:
    """The repo's own top-level manifest named `filename`, or None if it
    has no such file at its root -- deliberately ignores any same-named
    manifest discovery.py's `find_manifests` finds deeper in the tree (see
    this module's docstring for why root-only is the right scope here)."""
    candidate = repo / filename
    return candidate if candidate.is_file() else None


def canonical_fingerprints(
    repos: list[Path], filename: str, display_fn: Callable[[Path], str]
) -> dict[Path, str]:
    """repo -> fingerprint, for every repo in `repos` that has a root-level
    `filename` manifest. A repo with none at its root is simply absent
    from the returned dict -- it has no tooling identity of this kind to
    compare at all, which is distinct from `display_fn` returning
    "missing" (manifest present, but the tool's config isn't declared in
    it) -- see cross_repo_drift.py's docstring for how "missing" itself
    then participates in the majority vote."""
    result: dict[Path, str] = {}
    for repo in repos:
        manifest = root_manifest(repo, filename)
        if manifest is not None:
            result[repo] = display_fn(manifest)
    return result
