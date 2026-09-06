"""The remaining primary-axis checks (polyrepo, single-repo default) plus
detect_primary_type(), which runs the full five-way check in
detecting-repo-type.md's own listed order. See primary_signals.py for the
first three checks (meta-repo, monorepo, microservices).
"""
from __future__ import annotations

from pathlib import Path

from .constants import MANIFEST_ROOT_FILES, POLYREPO_FLEET_MIN_SIZE, POLYREPO_REGISTRY_MARKERS
from .primary_signals import detect_meta_repo, detect_microservices, detect_monorepo


def detect_polyrepo(repo: Path, portfolio_size: int, portfolio_shape_match: bool) -> tuple[str | None, str]:
    for marker in POLYREPO_REGISTRY_MARKERS:
        if (repo / marker).is_file():
            return marker, "polyrepo fleet with a registry"
    if portfolio_size >= POLYREPO_FLEET_MIN_SIZE and portfolio_shape_match:
        return (f"portfolio of {portfolio_size} similarly-shaped repos",
                "one member of a polyrepo fleet")
    return None, ""


def has_single_manifest_shape(repo: Path) -> bool:
    """A repo's own single-manifest-at-root shape, the same test the
    "org has 10+ similarly-shaped repos" polyrepo-fleet signal needs to
    compare across a portfolio -- true when exactly one of
    MANIFEST_ROOT_FILES exists and no monorepo/meta-repo marker is present."""
    manifests = [m for m in MANIFEST_ROOT_FILES if (repo / m).is_file()]
    if len(manifests) != 1:
        return False
    if detect_meta_repo(repo) is not None:
        return False
    marker, _ = detect_monorepo(repo)
    return marker is None


def detect_primary_type(repo: Path, repos: list[Path]) -> tuple[str, str, str]:
    """Returns (primary_type, signal, note). Checked in
    detecting-repo-type.md's own listed order; single_repo is the doc's own
    explicit default when nothing else matches."""
    signal = detect_meta_repo(repo)
    if signal:
        return "meta_repo", signal, "meta-repo / manifest repo"

    signal, note = detect_monorepo(repo)
    if signal:
        return "monorepo", signal, note

    signal, note = detect_microservices(repo)
    if signal:
        return "microservices", signal, note

    portfolio_shape_match = has_single_manifest_shape(repo) and sum(
        1 for r in repos if has_single_manifest_shape(r)
    ) >= POLYREPO_FLEET_MIN_SIZE
    signal, note = detect_polyrepo(repo, len(repos), portfolio_shape_match)
    if signal:
        return "polyrepo", signal, note

    return "single_repo", "no workspace file; one manifest at root (or none matched)", \
        "single repo (default assumption)"
