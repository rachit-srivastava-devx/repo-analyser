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


def commit_all_with_invalid_utf8_author(repo: Path, message: str) -> str:
    """Stages everything, then constructs the commit object *manually*
    (`git write-tree` + `git hash-object -w -t commit --stdin` +
    `git update-ref`) with an author name containing a raw invalid-UTF-8
    byte (0xFF) -- git itself never validates commit metadata encoding, so
    a real-world repo can end up with this. Bypasses git's own commit
    plumbing (which would refuse/mangle a bad env var) by writing the
    commit object's bytes directly, replicating the technique an
    independent verifier used to reproduce a real `UnicodeDecodeError`
    crash in this collector's `git blame` parsing. Returns the new commit
    sha; updates the current branch to point at it."""
    git(repo, "add", "-A")
    tree_sha = git(repo, "write-tree").stdout.strip()

    parent = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"],
                             cwd=repo, capture_output=True, text=True, env=_ENV)
    parent_line = f"parent {parent.stdout.strip()}\n" if parent.returncode == 0 else ""

    # \xff round-trips to the single raw byte 0xFF via latin-1 -- a byte
    # sequence that is not valid UTF-8 on its own.
    commit_text = (
        f"tree {tree_sha}\n"
        f"{parent_line}"
        f"author Test \xff Bytes <test@example.com> 1700000000 +0000\n"
        f"committer Test Bytes <test@example.com> 1700000000 +0000\n"
        f"\n{message}\n"
    )
    commit_bytes = commit_text.encode("latin-1")

    hash_result = subprocess.run(
        ["git", "hash-object", "-w", "-t", "commit", "--stdin"],
        cwd=repo, input=commit_bytes, capture_output=True, env=_ENV,
    )
    hash_result.check_returncode()
    commit_sha = hash_result.stdout.decode("ascii").strip()

    branch = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo,
                             capture_output=True, text=True, env=_ENV, check=True).stdout.strip()
    subprocess.run(["git", "update-ref", f"refs/heads/{branch}", commit_sha],
                    cwd=repo, check=True, env=_ENV)
    return commit_sha
