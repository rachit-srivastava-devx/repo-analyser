"""Top-level orchestration for resolving a single PR's base/head/merge-base
commit range -- the one serialization point every other pr_review module
depends on, so that logic exists exactly once rather than being re-derived
(and possibly re-diverging) in each downstream module.

Precedence for base/head, and the merge-base computation itself, are each
owned by their own submodule -- see `ref_resolution.py` (precedence order
and ref validation), `github_event.py` (the GITHUB_EVENT_PATH fallback),
and `merge_base.py` (the merge-base git call and its shallow-clone
diagnostics) for the actual rationale. This module just calls them in
order and shapes the result into a `PrContext`.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..core.util import run, write_json
from .context_models import PrContext
from .merge_base import _merge_base
from .ref_resolution import _resolve_base_head


def resolve_pr_context(repo: Path, base: str | None = None, head: str | None = None) -> PrContext:
    """Pure: resolves base/head, computes merge_base and commits_in_range,
    and returns a PrContext. Does not write anything -- see `run_context`.
    """
    base_sha, head_sha, resolved_via = _resolve_base_head(repo, base, head)
    merge_base_sha = _merge_base(repo, base_sha, head_sha)

    warning = None
    if merge_base_sha == head_sha and head_sha != base_sha:
        warning = (
            f"head ({head_sha}) is an ancestor of base ({base_sha}) -- "
            "--base/--head may be swapped. The merge_base..head diff range "
            "is empty even though base and head differ."
        )

    commits_in_range = int(
        run(["git", "rev-list", "--count", f"{merge_base_sha}..{head_sha}"], cwd=repo).stdout.strip()
    )

    return PrContext(
        repo=repo.name,
        base_sha=base_sha,
        head_sha=head_sha,
        merge_base_sha=merge_base_sha,
        resolved_via=resolved_via,
        commits_in_range=commits_in_range,
        warning=warning,
    )


def run_context(repo: Path, out_dir: Path, base: str | None = None, head: str | None = None) -> Path:
    """Calls `resolve_pr_context` and persists the result as
    `out_dir/pr_review_context.json` (mirrors every `collectors/*.py`
    module's `analyze_x` (pure) / `run_x` (writes, returns Path) split)."""
    ctx = resolve_pr_context(repo, base, head)
    out_path = out_dir / "pr_review_context.json"
    write_json(out_path, asdict(ctx))
    return out_path
