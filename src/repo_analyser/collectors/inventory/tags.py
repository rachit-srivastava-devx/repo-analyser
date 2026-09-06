"""Most-recent-git-tag-date lookup, split out of changelog.py so that module
stays focused on the changelog file itself. Mirrors churn.py's existing
shell-out-via-run() pattern (no GitPython dependency anywhere in this
project).
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ...core.util import run


def latest_tag_date(repo: Path) -> date | None:
    """Equivalent to `git for-each-ref refs/tags --sort=-creatordate
    --format='%(creatordate:short)' | head -1`. Empty stdout (no tags) is a
    normal, zero-exit-code outcome, not an error."""
    res = run(["git", "for-each-ref", "refs/tags", "--sort=-creatordate",
               "--format=%(creatordate:short)"], cwd=repo)
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return datetime.strptime(lines[0], "%Y-%m-%d").date()
    except ValueError:
        return None
