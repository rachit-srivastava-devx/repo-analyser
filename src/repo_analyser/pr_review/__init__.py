"""Per-PR diff-scoped review: resolves a PR's base/head/merge-base commit
range once (context.py) and extracts its changed-file set and added-line
ranges (diff.py), so every other module built on top of this subpackage
works from one shared, already-validated PrContext instead of each
re-deriving base/head/merge-base independently and possibly disagreeing.

Every diff in this subpackage is computed FROM merge_base, never from base
directly: a plain `base..head` two-dot diff conflates base's own commits
since the PR forked with head's actual changes (see diff.py's module
docstring for why, and its tests for a worked example where the two
disagree). This is the one property every downstream consumer of this
subpackage depends on.
"""
from __future__ import annotations

from .context import PrContext, resolve_pr_context, run_context
from .diff import ChangedFile, get_changed_files, run_diff

__all__ = ["ChangedFile", "PrContext", "get_changed_files", "resolve_pr_context", "run_context", "run_diff"]
