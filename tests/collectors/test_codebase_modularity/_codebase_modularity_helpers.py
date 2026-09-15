"""Shared fixture-building helpers for the codebase_modularity test
package. Named per-collector (not the generic `_helpers.py`) because
tests/ has no `__init__.py` anywhere -- pytest's prepend import mode means
a generic name would collide with every other collector's identically-
named helper module in sys.modules the moment the full suite runs
together (AGENTS.md §4)."""
from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                           text=True, env=_ENV)


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


def make_source_file(repo: Path, rel: str, lines: int) -> Path:
    """A syntactically-harmless source file with exactly `lines` physical
    lines, so a test can pin the oversized-file threshold to an exact
    boundary (500 vs 501) rather than an approximate line count."""
    body = "\n".join(f"x{i} = {i}" for i in range(lines))
    return write(repo, rel, body + "\n")


def class_with_method_count(name: str, method_count: int) -> str:
    """A Python module defining one class named `name` with exactly
    `method_count` direct, trivial methods (2 physical lines each) -- lets
    a test pin the method-count god-class threshold to an exact boundary
    (20 vs 21) without the class's own LOC ever approaching the separate
    300-line LOC threshold."""
    if method_count == 0:
        return f"class {name}:\n    pass\n"
    methods = "\n".join(f"    def m{i}(self):\n        return None" for i in range(method_count))
    return f"class {name}:\n{methods}\n"


def class_with_exact_loc(name: str, total_loc: int) -> str:
    """A Python module defining one class named `name`, with a single
    trivial method (well under the method-count threshold), padded so the
    class's own LOC (`end_lineno - lineno + 1`) is exactly `total_loc` --
    lets a test pin the LOC god-class threshold to an exact boundary (300
    vs 301). `total_loc` must be >= 3 (class line + def line + return
    line)."""
    assert total_loc >= 3
    pad = total_loc - 3
    lines = [f"class {name}:", "    def m0(self):"]
    lines += [f"        p{i} = {i}" for i in range(pad)]
    lines.append("        return None")
    return "\n".join(lines) + "\n"
