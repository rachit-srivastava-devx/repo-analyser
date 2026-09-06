"""Git-index-backed file listing for this collector.

Deliberately NOT reusing repo_type/fileio.py's `tracked_files`: that helper
crawls the working-tree disk (rglob) and excludes vendor/build dirs by name
(core.lang.EXCLUDE_DIR_PARTS), independent of git entirely. CODEOWNERS
coverage is specifically a statement about the tracked file tree -- a repo
can have real, meaningful CODEOWNERS rules for paths a disk-crawl would
exclude by name (e.g. a rule for a deliberately-committed `vendor/`
directory), and `git ls-files` is both the more correct source of truth
here and already excludes untracked build output with no separate
exclusion list needed. Collector internals also aren't for cross-import
(docs/ARCHITECTURE.md), so a small dedicated helper is the right shape
either way.
"""
from __future__ import annotations

from pathlib import Path

from ...core.util import run


def tracked_files(repo: Path) -> list[Path]:
    """Every path git considers tracked (the index), relative to `repo`.
    Reflects `git add`ed-but-uncommitted files too, since `ls-files` reads
    the index, not HEAD."""
    result = run(["git", "ls-files"], cwd=repo)
    return [Path(line) for line in result.stdout.splitlines() if line]
