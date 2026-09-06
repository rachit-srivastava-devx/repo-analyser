"""Lint/format config divergence comparison -- generic across eslint,
ruff, and golangci: given every manifest that OWNS a config of one kind
(package.json -> eslint, pyproject.toml -> ruff, go.mod -> golangci),
compares their fingerprints (see lint_configs.py) and reports the
minority-vs-majority split as drift.

`LINT_KIND_SPECS` is the registry tying each kind's owning-manifest
filename to its own fingerprint function -- analyze.py drives all three
off this one tuple rather than three hand-written branches.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path

from .lint_configs import eslint_display, golangci_display, ruff_display
from .models import ToolingDriftRow


def check_lint_config_drift(
    repo: Path, owning_manifests: list[Path], config_kind: str, display_fn: Callable[[Path], str]
) -> ToolingDriftRow | None:
    """`owning_manifests` must already have >= MIN_MANIFESTS_TO_COMPARE
    entries (caller's responsibility -- this only decides whether they
    AGREE, not whether there were enough to compare). Compares every
    owning manifest's `display_fn` fingerprint; if they don't all match,
    the minority-vs-majority split is the drift. `drift_detail` lists
    EVERY owning manifest's own state (not just the outliers), formatted
    as `<repo-relative-path>:<state>` -- "pairs", per this module's own
    brief, meaning both sides of the divergence are visible, not just
    "which one is wrong"."""
    displays = {p: display_fn(p) for p in owning_manifests}
    counts = Counter(displays.values())
    if len(counts) <= 1:
        return None  # identical config state across every owning manifest -- no drift.
    majority_state = counts.most_common(1)[0][0]
    drifted = sum(1 for v in displays.values() if v != majority_state)
    detail = [f"{p.relative_to(repo)}:{displays[p]}" for p in sorted(owning_manifests)]
    return ToolingDriftRow(
        repo=repo.name, config_kind=config_kind,
        packages_compared=len(owning_manifests), packages_with_drift=drifted,
        drift_detail=";".join(detail), skip_reason="",
    )


LINT_KIND_SPECS: tuple[tuple[str, str, Callable[[Path], str]], ...] = (
    ("eslint", "package.json", eslint_display),
    ("ruff", "pyproject.toml", ruff_display),
    ("golangci", "go.mod", golangci_display),
)
