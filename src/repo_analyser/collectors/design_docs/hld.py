"""HLD presence & freshness. Presence checks a fixed, conventional path list
(models.HLD_CANDIDATES) via the filesystem -- every candidate found is
reported, not just the first (a repo can have both a root ARCHITECTURE.md
and a more detailed docs/architecture.md at once).

Freshness reports two independent "days since" numbers, both relative to
`now` (same convention as inventory/commit_activity.py's own
days_since_last_commit), and leaves the comparison to the reader rather
than banding them into a verdict -- this checklist item explicitly asks for
a staleness *signal*, not a binary judgment."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .git_dates import doc_last_commit_epoch, repo_last_commit_epoch
from .models import HLD_CANDIDATES


@dataclass
class HldSignal:
    has_hld: bool
    docs_found: list[str]
    untracked_count: int
    days_since_doc_touched: int | None
    days_since_repo_last_commit: int | None
    repo_has_commits: bool


def find_hld_candidates(repo: Path) -> list[str]:
    """Every HLD_CANDIDATES entry that exists, as repo-relative POSIX paths,
    sorted for deterministic output."""
    return sorted(rel for rel in HLD_CANDIDATES if (repo / rel).is_file())


def collect_hld_signal(repo: Path, now: datetime) -> HldSignal:
    docs = find_hld_candidates(repo)
    repo_epoch = repo_last_commit_epoch(repo)
    repo_has_commits = repo_epoch is not None
    now_epoch = int(now.timestamp())

    days_since_repo_commit = (now_epoch - repo_epoch) // 86400 if repo_epoch is not None else None

    if not docs:
        return HldSignal(False, [], 0, None, days_since_repo_commit, repo_has_commits)

    doc_epochs = [doc_last_commit_epoch(repo, rel) for rel in docs]
    untracked_count = sum(1 for e in doc_epochs if e is None)
    tracked_epochs = [e for e in doc_epochs if e is not None]
    # The most-recently-touched tracked candidate stands in for "the HLD"
    # when more than one exists -- the freshest one is the relevant one for
    # a freshness signal; an untracked-only set has no freshness to report.
    freshest = max(tracked_epochs) if tracked_epochs else None
    days_since_doc_touched = (now_epoch - freshest) // 86400 if freshest is not None else None

    return HldSignal(
        has_hld=True,
        docs_found=docs,
        untracked_count=untracked_count,
        days_since_doc_touched=days_since_doc_touched,
        days_since_repo_last_commit=days_since_repo_commit,
        repo_has_commits=repo_has_commits,
    )
