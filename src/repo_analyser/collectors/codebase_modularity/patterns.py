"""Shared sampling constant + capped-join helper for this package's three
independent signals -- same SAMPLE_CAP/join_sample convention as
migration_hygiene/patterns.py + text_io.py, kept local to this package
rather than imported cross-collector (each collector is its own
independent module, docs/ARCHITECTURE.md)."""
from __future__ import annotations

# Bounded sample size for every ";"-joined list field in the result -- an
# unbounded join is how a huge monorepo (AGENTS.md §3's "huge" rung) turns
# one CSV cell into a multi-megabyte string. Every *_count field always
# reports the true total, never the truncated sample's length.
SAMPLE_CAP = 10


def join_sample(items: list[str], cap: int = SAMPLE_CAP) -> str:
    """";"-joined sample, capped at `cap` entries with a "+N more" suffix
    when truncated. The caller always reports the true count separately --
    this string is a preview, never the source of truth for "how many"."""
    if len(items) <= cap:
        return ";".join(items)
    shown = items[:cap]
    return ";".join(shown) + f";+{len(items) - cap} more"
