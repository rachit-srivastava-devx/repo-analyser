"""The data shape every other pr_review module builds on: one resolved PR
commit range, computed exactly once (see context.py's `resolve_pr_context`)
so it exists in one place rather than being re-derived independently by
each downstream module.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PrContext:
    repo: str
    base_sha: str
    head_sha: str
    merge_base_sha: str
    resolved_via: str  # "explicit" | "github_event"
    commits_in_range: int
    # None in the common case. Set when head_sha resolves to be an ancestor
    # of base_sha (merge_base_sha == head_sha while head_sha != base_sha) --
    # the signature of a swapped --base/--head: the merge_base..head range
    # is then empty even though base and head genuinely differ, which would
    # otherwise look like "a PR with no changes" for a completely different
    # and much more mundane reason (a typo'd CLI invocation).
    warning: str | None = None
