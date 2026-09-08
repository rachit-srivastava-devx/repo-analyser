"""Shared git-repo fixture helpers for doc_quality's split test suite.
Named `_doc_quality_helpers.py`, never the generic `_helpers.py` -- nothing
under tests/ has an `__init__.py` (pytest prepend-import mode), so a
generic helper name would collide in sys.modules with every other
collector's identically-named helper the moment the full suite runs
together (AGENTS.md SS4)."""
from __future__ import annotations

import subprocess
from pathlib import Path

# Same minimal, deterministic env as tests/conftest.py's own `_git` helper --
# duplicated locally (not imported) since this needs per-call date control
# (GIT_AUTHOR_DATE/GIT_COMMITTER_DATE) that the shared fixture doesn't, and
# this task's scope is this test package only.
BASE_ENV = {
    "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
}

# Same convention as tests/collectors/test_mutation.py's HAS_MUTMUT: interrogate
# is this project's own dev-tool dependency, not guaranteed present on every
# runner -- tests that need a *real* interrogate invocation skip rather than
# fail when it's absent. (The truly-empty-directory case doesn't need this
# guard: it's caught by a pure-Python "nothing to scan" check before this
# module ever tries to invoke interrogate at all.)
HAS_INTERROGATE = subprocess.run(["which", "interrogate"], capture_output=True).returncode == 0


def git(repo: Path, *args: str, date: str | None = None) -> None:
    env = dict(BASE_ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=env)


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")


def commit(repo: Path, filename: str, content: str, date: str, message: str = "commit") -> None:
    (repo / filename).write_text(content)
    git(repo, "add", filename)
    git(repo, "commit", "-q", "-m", message, date=date)


def lightweight_tag(repo: Path, name: str) -> None:
    """Creatordate resolves to the currently-checked-out commit's own
    committer date for a lightweight tag (confirmed live -- see
    changelog_staleness.py's docstring), so no separate date needs to be
    passed here."""
    git(repo, "tag", name)
