"""Shared test-fixture builder for pr_review's test package."""
from __future__ import annotations

from repo_analyser.pr_review.context import PrContext


def _ctx(merge_base_sha: str, head_sha: str) -> PrContext:
    """A minimal PrContext for tests that only exercise diff.py -- only
    merge_base_sha/head_sha are read by get_changed_files; the rest are
    placeholders."""
    return PrContext(
        repo="placeholder", base_sha=merge_base_sha, head_sha=head_sha,
        merge_base_sha=merge_base_sha, resolved_via="explicit", commits_in_range=0,
    )
