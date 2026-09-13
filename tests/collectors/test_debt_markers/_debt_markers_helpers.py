"""Shared fixture-building helpers for the debt_markers test package. Named
per-collector (not the generic `_helpers.py`) because tests/ has no
`__init__.py` anywhere -- pytest's prepend import mode means a generic name
would collide with every other collector's identically-named helper module
in sys.modules the moment the full suite runs together (see this repo's
"Test-helper naming" convention, same rationale as _codebase_modularity_
helpers.py / _flag_debt_helpers.py)."""
from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
}


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                           text=True, env=env or _ENV)


def init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    return repo


def write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def write_bytes(repo: Path, rel: str, data: bytes) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def commit_all_at(repo: Path, message: str, iso_date: str) -> None:
    """Same as commit_all, but pins both author and committer dates (git's
    `--date`/`GIT_AUTHOR_DATE` accept an ISO-8601 string) -- lets a test
    plant a marker at a known, exact age instead of "sometime after
    init"."""
    env = dict(_ENV, GIT_AUTHOR_DATE=iso_date, GIT_COMMITTER_DATE=iso_date)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, env=env)
