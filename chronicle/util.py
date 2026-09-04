"""Shared helpers: subprocess execution, repo discovery, CSV I/O.

Design rule for this whole tool: a module either returns real computed data,
or raises ToolExecutionError with the captured stderr. It never returns an
empty/zero result silently for something that should have found data — see
CHRONICLE-ADR-001 in docs/METHODOLOGY.md.
"""
from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class ToolExecutionError(RuntimeError):
    """Raised when an external tool exits non-zero and the caller has no
    documented reason to treat that as a legitimate empty result."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"command failed ({returncode}): {' '.join(cmd)}\n--- stderr ---\n{stderr[:2000]}"
        )


@dataclass
class RunResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600,
        check: bool = True, input_text: str | None = None,
        extra_path: str | None = None) -> RunResult:
    """Run a subprocess and capture output as text. Raises ToolExecutionError
    on non-zero exit when check=True (the default) -- callers that expect a
    tool to sometimes exit non-zero on legitimate findings (e.g. gitleaks
    finds a secret, semgrep finds a match) must pass check=False and inspect
    returncode themselves, explicitly, rather than defaulting to swallowing
    every failure mode.

    extra_path: prepended to PATH for this call only. Used to force a
    specific Node version (this portfolio's package.json declares
    node>=20; the host's default node is v26, under which a transitive
    dependency of jsonwebtoken crashes on startup -- see
    docs/METHODOLOGY.md, "Node version pin")."""
    import os
    env = None
    if extra_path:
        env = dict(os.environ)
        env["PATH"] = f"{extra_path}:{env.get('PATH', '')}"
    proc = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
        timeout=timeout, input=input_text, env=env,
    )
    if check and proc.returncode != 0:
        raise ToolExecutionError(cmd, proc.returncode, proc.stderr)
    return RunResult(cmd, proc.returncode, proc.stdout, proc.stderr)


def is_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir()


def discover_repos(target: Path) -> list[Path]:
    """A target is either a single git repo, or a directory containing one
    or more git repos as immediate children (a portfolio). Anything else is
    an error -- we do not silently return an empty list for a typo'd path."""
    target = target.resolve()
    if not target.exists():
        raise FileNotFoundError(f"target does not exist: {target}")
    if is_git_repo(target):
        return [target]
    children = sorted(p for p in target.iterdir() if p.is_dir() and is_git_repo(p))
    if not children:
        raise ValueError(
            f"{target} is neither a git repo nor a directory of git repos "
            "(no immediate child has a .git dir)"
        )
    return children


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> int:
    """Writes rows to CSV, returns the row count actually written. A caller
    that gets 0 back and expected >0 must decide what that means -- this
    function will not paper over it by skipping the file."""
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fn = fieldnames or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def read_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)
