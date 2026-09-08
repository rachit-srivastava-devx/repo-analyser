"""Full-git-history blob enumeration, shared by db_files.py. Split out to
keep both files under the ~80-line convention (AGENTS.md §4).

`git cat-file -p` output can be arbitrary binary (a real SQLite file), so
`_blob_content` deliberately skips `core.util.run()` -- `run()` hardcodes
`text=True`, which corrupts non-UTF8 bytes, exactly what db_files.py's
SQLite-header check inspects. A documented, narrow exception to AGENTS.md
§3's "use run()" rule; every other git call in this module still goes
through run().
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from ...core.util import run

_CAT_FILE_TIMEOUT_S = 30


def blobs_by_path(repo: Path, matches_extension: Callable[[str], bool]) -> dict[str, set[str]]:
    """{path: {blob_sha, ...}} for every candidate-extension path, at any
    point in full history. `git rev-list --objects --all` prints nothing
    (exit 0, empty stdout) for a zero-commit repo -- no special-casing
    needed for "empty". Keeps every sha ever seen per path, not just the
    newest -- a later commit can overwrite the same path with unrelated
    content before deleting it, so checking only the newest blob would
    miss a real dump/db file that existed there earlier."""
    res = run(["git", "rev-list", "--objects", "--all"], cwd=repo)
    by_path: dict[str, set[str]] = {}
    for line in res.stdout.splitlines():
        sha, _, path = line.partition(" ")
        if path and matches_extension(path):
            by_path.setdefault(path, set()).add(sha)
    return by_path


def blob_content(repo: Path, sha: str) -> bytes:
    """Raw bytes for one blob. Returns b"" for any failure (bad sha,
    timeout, git error) -- one unreadable historical blob must not crash
    the whole collector run (AGENTS.md §3 rung 3)."""
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-p", sha], cwd=repo, capture_output=True,
            timeout=_CAT_FILE_TIMEOUT_S, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return b""
    return proc.stdout if proc.returncode == 0 else b""


def still_tracked(repo: Path, path: str) -> bool:
    """Whether `path` is still tracked at HEAD -- "still part of what a
    fresh clone gets today", not "does a file exist on disk", which could
    disagree with HEAD under uncommitted working-tree changes."""
    res = run(["git", "ls-tree", "-r", "HEAD", "--name-only", "--", path], cwd=repo)
    return path in res.stdout.splitlines()
