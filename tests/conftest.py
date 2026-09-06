"""Shared fixtures. Real git repos in a tmp dir, not mocked git output --
this tool's own AGENTS.md (§2) says a check that can't tell a real failure
from a fake pass isn't a check; mocking `git log` output is exactly the kind
of proxy that would let a real parser regression through.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.com",
             "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.com",
             "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
    )


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """A directory that is neither a git repo nor contains one -- the
    canonical invalid-target case for discover_repos."""
    d = tmp_path / "not_a_repo"
    d.mkdir()
    return d


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A real, minimal git repo: two commits, one author, one file changed
    across both so churn/complexity/ontology have something real to see."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "app.py").write_text("def add(a, b):\n    return a + b\n")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "feat: add add()")
    (repo / "app.py").write_text("def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "fix: add sub()")
    return repo


@pytest.fixture
def git_worktree(git_repo: Path, tmp_path: Path) -> Path:
    """A real `git worktree add` checkout of `git_repo` -- its .git is a
    *file* (containing "gitdir: ..."), not a directory, unlike a normal
    clone. Regression fixture for the is_git_repo/discover_repos bug where
    such paths were rejected outright."""
    worktree = tmp_path / "sample_worktree"
    _git(git_repo, "worktree", "add", "-q", str(worktree), "-b", "wt-branch")
    return worktree


@pytest.fixture
def git_portfolio(tmp_path: Path) -> Path:
    """A directory of 2 independent git repos as immediate children -- the
    portfolio shape discover_repos must also accept."""
    portfolio = tmp_path / "portfolio"
    portfolio.mkdir()
    for name, msg in [("repo-a", "feat: init a"), ("repo-b", "docs: init b")]:
        repo = portfolio / name
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "README.md").write_text(f"{name}\n")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-q", "-m", msg)
    return portfolio
