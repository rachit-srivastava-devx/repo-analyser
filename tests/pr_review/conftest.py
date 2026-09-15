"""Fixtures for pr_review tests.

`diverged_repo` is the load-bearing fixture here: base and head genuinely
diverge from a shared fork point -- base picks up its own commits after the
fork, head picks up its own, separately -- NOT a simple linear history.

That divergence matters because on a simple linear history, a two-dot
(`base..head`) and three-dot-equivalent (`merge_base..head`) diff report the
identical changed-file set: there ARE no base-only changes for a two-dot
diff to wrongly pick up. A fixture built that way would let a real
regression (diffing from `base_sha` instead of `merge_base_sha`) pass this
test suite silently. `diverged_repo` gives base its own independent commits
after the fork specifically so the two diffs disagree, and a test can
assert on that disagreement directly.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

# PATH order matters: Homebrew's real git must come before /usr/bin's Xcode
# CLT stub, which refuses to run at all until the Xcode license is accepted
# (exit 69) -- see tests/conftest.py's `_git()` for the full incident this
# was copied from, and docs/METHODOLOGY.md item #42.
_ENV = {
    "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=_ENV,
    ).stdout


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


@dataclass
class DivergedRepo:
    """base and head share `fork_sha` as their sole common ancestor, then
    diverge onto separate lines of commits:

    ```
                       fork_sha
                      /        \\
        base: unrelated change 1   head: add feature file
                   |                          |
        base: unrelated change 2   head: extend feature
                   |                          |
                base_sha                   head_sha
    ```

    `base_only_files`: paths that changed ONLY on the base line after the
    fork. A correct `merge_base..head` diff must NOT include these; a
    buggy two-dot `base..head` diff incorrectly does -- this is exactly
    what test_diff.py's regression test asserts.

    `head_only_files`: paths that changed ONLY on the head line after the
    fork -- the PR's real content. These must appear in both a correct and
    a buggy diff alike (a two-dot diff is wrong because it ALSO includes
    base-only noise, not because it excludes real content).
    """
    repo: Path
    fork_sha: str
    base_sha: str
    head_sha: str
    base_only_files: frozenset[str]
    head_only_files: frozenset[str]


@pytest.fixture
def diverged_repo(tmp_path: Path) -> DivergedRepo:
    repo = tmp_path / "diverged"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")

    (repo / "shared.txt").write_text("v1\n")
    fork_sha = _commit(repo, "fork point")
    _git(repo, "branch", "feature", "main")

    # base line: two commits that happen on the branch the PR targets,
    # after the fork -- unrelated to the PR itself.
    (repo / "shared.txt").write_text("v2\n")
    _commit(repo, "base: unrelated change 1")
    (repo / "base_only.txt").write_text("only on base\n")
    base_sha = _commit(repo, "base: unrelated change 2")

    # head line: two commits that ARE the PR's real content.
    _git(repo, "checkout", "-q", "feature")
    (repo / "feature.txt").write_text("feature work 1\n")
    _commit(repo, "head: add feature file")
    (repo / "feature.txt").write_text("feature work 1\nmore\n")
    head_sha = _commit(repo, "head: extend feature")

    return DivergedRepo(
        repo=repo,
        fork_sha=fork_sha,
        base_sha=base_sha,
        head_sha=head_sha,
        base_only_files=frozenset({"shared.txt", "base_only.txt"}),
        head_only_files=frozenset({"feature.txt"}),
    )
