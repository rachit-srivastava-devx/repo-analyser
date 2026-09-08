"""Git-history date/content helpers shared by hld.py and adr_status_git.py.
Every call uses check=False deliberately: a zero-commit repo, or a path with
no git history at all (untracked/uncommitted), is a real, expected, non-
crashing result here -- git itself exits non-zero for "no commits yet" with
empty stdout, and this module reads that as None/empty rather than letting
`run`'s default check=True turn it into a ToolExecutionError. A genuine git
failure (corrupt repo, git not on PATH) produces the same empty-stdout
shape and is not distinguished from "zero commits" -- acceptable here
because `analyze_repo` is only ever called on a path `discover_repos`
already confirmed is a git repo."""
from __future__ import annotations

from pathlib import Path

from ...core.util import run


def repo_last_commit_epoch(repo: Path) -> int | None:
    """Unix timestamp of the repo's own most-recent commit on the checked-
    out ref, or None for a repo with zero commits."""
    res = run(["git", "log", "-1", "--format=%ct"], cwd=repo, check=False)
    out = res.stdout.strip()
    return int(out) if out else None


def doc_last_commit_epoch(repo: Path, rel_path: str) -> int | None:
    """Unix timestamp of the most recent commit touching this path, or None
    when the path has no git history at all -- an untracked/uncommitted
    file. Presence detection for this collector's HLD/ADR discovery
    deliberately walks the filesystem, not `git ls-files` (api_contract's/
    migration_hygiene's own precedent: a gitignored-but-present file still
    counts as existing); freshness is inherently a git-history question
    though, so git IS consulted here, and an untracked file genuinely has
    no freshness signal to report.

    Falls back to a case-insensitive pathspec (git's `:(icase)` magic) only
    when the exact-case lookup comes back empty. Filesystem existence
    (`find_hld_candidates`'s `is_file()` check) is case-insensitive on
    macOS/Windows, but git's own pathspec matching in `git log -- <path>`
    is always case-sensitive -- so a candidate like "docs/architecture.md"
    that's genuinely tracked under "docs/ARCHITECTURE.md" (or vice versa)
    would otherwise come back with no history and get miscounted into
    hld_untracked_count as if it were never committed, when the underlying
    file is tracked fine, just under different-case pathspec. Exact match
    is tried first and preferred so two genuinely distinct, differently-
    cased files on a case-sensitive filesystem (most CI Linux runners) each
    still resolve to their own history, never blended -- the icase retry
    only fires on the empty-result path, where there is nothing to blend."""
    res = run(["git", "log", "-1", "--format=%ct", "--", rel_path], cwd=repo, check=False)
    out = res.stdout.strip()
    if out:
        return int(out)
    res = run(["git", "log", "-1", "--format=%ct", "--", f":(icase){rel_path}"], cwd=repo, check=False)
    out = res.stdout.strip()
    return int(out) if out else None


def commit_hashes_touching(repo: Path, rel_path: str) -> list[str]:
    """Oldest-to-newest commit hashes that touched this path (--follow to
    survive a rename). Empty list for an untracked path -- same "no
    history" signal as doc_last_commit_epoch, not a crash.

    Deliberately does NOT pass --reverse to git itself: `--follow` combined
    with `--reverse` is a real git quirk where rename-following silently
    breaks, truncating the result to only the commits since the file's
    CURRENT path and losing everything before the rename (reproduced and
    confirmed during this fix -- a 4-commit rename history collapsed to 1).
    Git log's plain (newest-first) output correctly follows the full rename
    chain, so that's what's fetched here, then reversed in Python to hand
    callers the oldest-to-newest order they already expect."""
    res = run(["git", "log", "--follow", "--format=%H", "--", rel_path],
              cwd=repo, check=False)
    commits = [line for line in res.stdout.splitlines() if line.strip()]
    return commits[::-1]


def content_at_commit(repo: Path, commit: str, rel_path: str) -> str | None:
    """Text content of rel_path as of `commit`, or None if the show fails.
    A rename edge case that `--follow` didn't fully resolve is not chased
    further here -- reported as unreadable-at-that-revision (skipped, not
    a crash), rather than adding a second rename-tracking pass."""
    res = run(["git", "show", f"{commit}:{rel_path}"], cwd=repo, check=False)
    return res.stdout if res.returncode == 0 else None
