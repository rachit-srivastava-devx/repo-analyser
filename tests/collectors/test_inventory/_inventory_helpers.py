from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
}


def _git(repo: Path, *args: str, env_overrides: dict[str, str] | None = None) -> None:
    env = dict(_ENV)
    if env_overrides:
        env.update(env_overrides)
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=env)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    return path


def _commit_on_date(repo: Path, filename: str, content: str, message: str, date_iso: str) -> None:
    """date_iso like '2024-01-15T00:00:00' -- sets author and committer date
    so a test can build a repo with a fully controlled commit history (and,
    via a lightweight tag on that commit, a fully controlled tag date too:
    `%(creatordate)` for a lightweight tag is the underlying commit's own
    committer date, not the wall-clock time `git tag` happened to run)."""
    (repo / filename).write_text(content)
    _git(repo, "add", filename)
    _git(repo, "commit", "-q", "-m", message,
         env_overrides={"GIT_AUTHOR_DATE": date_iso, "GIT_COMMITTER_DATE": date_iso})
