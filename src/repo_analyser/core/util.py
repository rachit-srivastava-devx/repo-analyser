"""Shared helpers: subprocess execution, repo discovery, CSV I/O, and a
resource-aware thread pool for the common "one subprocess call per repo"
collector shape (see `run_concurrent`).

Design rule for this whole tool: a module either returns real computed data,
or raises ToolExecutionError with the captured stderr. It never returns an
empty/zero result silently for something that should have found data — see
docs/adr/0001-fail-loud-not-silent.md.
"""
from __future__ import annotations

import csv
import json
import os
import re
import signal
import subprocess
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar


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
        extra_path: str | None = None, extra_env: dict[str, str] | None = None) -> RunResult:
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
    docs/METHODOLOGY.md, "Node version pin").

    extra_env: merged into this call's environment (never removed
    afterward -- os.environ itself is never mutated). Used to pass npm's
    `npm_config_<key>` config-via-env-var convention (e.g.
    `{"npm_config_ignore_scripts": "true"}`) to commands like `npx` that
    have no equivalent CLI flag of their own -- see
    docs/ARCHITECTURE.md's "Security model" section for why this matters:
    this tool installs its own chosen npm packages (Stryker, dependency-
    cruiser) *inside* whatever arbitrary target repo it's pointed at, so a
    compromised repo's own `.npmrc`/registry config could otherwise try to
    hijack that install via a malicious postinstall script.

    On timeout, kills the whole process *group*, not just the direct
    child -- a real, confirmed bug found live (docs/METHODOLOGY.md #30): a
    `jscpd` run this tool reported as "timed out after 900 seconds" was
    still alive and burning CPU 15+ minutes later, reparented to `launchd`
    (ppid 1), because the plain `subprocess.run(..., timeout=...)` this
    used to call only kills the direct child it spawned -- jscpd's own JS
    entry point had already spawned its native `jscpd-darwin-arm64` binary
    as a *grandchild*, which the timeout never touched. `start_new_session
    =True` (not `preexec_fn` -- that runs in the forked child before
    exec(), the identical fork-unsafety hazard class that caused this
    tool's real kernel panic, docs/METHODOLOGY.md #23) puts the whole tree
    in its own process group so `os.killpg` can take it all down at once.
    A timeout that doesn't actually free the resources it was meant to
    bound is nearly as dangerous as no timeout, especially for a tool
    whose own operating history includes real crashes from uncontrolled
    subprocess resource use."""
    env = None
    if extra_path or extra_env:
        env = dict(os.environ)
        if extra_path:
            env["PATH"] = f"{extra_path}:{env.get('PATH', '')}"
        if extra_env:
            env.update(extra_env)
    proc = subprocess.Popen(
        cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if input_text is not None else None,
        text=True, env=env, start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait()
        raise
    if check and proc.returncode != 0:
        raise ToolExecutionError(cmd, proc.returncode, stderr)
    return RunResult(cmd, proc.returncode, stdout, stderr)


# Same signal and threshold as this machine's own ~/.claude/hooks/resource-
# safety-gate: swap usage, not free-RAM pages (macOS keeps those low even
# when healthy). ~350MB used was measured as this machine's healthy
# baseline; 17.9-20.5GB used was measured during two real 2026-09-04/05
# crash incidents (see docs/METHODOLOGY.md #29). Kept numerically identical
# to that hook on purpose, but not imported from it -- that hook lives in
# the user's own Claude Code config, outside this package, not something
# this tool should depend on.
SWAP_UNSAFE_THRESHOLD_MB = 6000.0

T = TypeVar("T")
R = TypeVar("R")


def _swap_used_mb() -> float | None:
    """macOS-only signal (`sysctl vm.swapusage`). Returns None on any
    failure -- wrong platform, sysctl missing, unparseable output -- so a
    caller fails open (proceeds at full requested concurrency) rather than
    crashing or silently forcing sequential execution when the signal
    simply can't be read."""
    try:
        proc = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True,
                               text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"used\s*=\s*([\d.]+)M", proc.stdout)
    return float(m.group(1)) if m else None


def safe_worker_count(requested: int) -> int:
    """Caps a thread-pool worker count to 1 (sequential -- never 0, which
    would just hang) when swap is already at/above
    `SWAP_UNSAFE_THRESHOLD_MB`; returns `requested` unchanged otherwise,
    including when the signal can't be read at all."""
    used = _swap_used_mb()
    if used is not None and used >= SWAP_UNSAFE_THRESHOLD_MB:
        return 1
    return max(1, requested)


def run_concurrent(items: Iterable[T], fn: Callable[[T], R], max_workers: int = 4) -> list[R]:
    """Runs `fn(item)` for every item, in a small thread pool -- safe for
    the "one subprocess call per repo" shape most collectors use:
    `subprocess.run()` releases the GIL for the whole time it's waiting on
    the child process, so threads get real wall-clock concurrency on
    I/O-bound work with zero new fork-safety surface (no new processes are
    ever forked by this function itself).

    Backs off to fully sequential (see `safe_worker_count`) when swap is
    already under real pressure. Return order matches `items`
    (`ThreadPoolExecutor.map`'s own guarantee); an exception raised by
    `fn` propagates once every already-submitted call has finished (the
    `with` block's own `shutdown(wait=True)`) -- the same failure
    behavior a plain `[fn(i) for i in items]` already had, so this is a
    drop-in replacement, not a semantic change.

    Deliberately NOT safe for, and not used by, mutation testing: mutmut
    and Stryker each already fork their own worker subprocesses
    internally, and stacking this tool's own thread-level concurrency on
    top would multiply the exact macOS fork-crash hazard that caused a
    real kernel panic (docs/METHODOLOGY.md #23), not just add load.
    Mutation testing stays sequential -- see mutation.py's module
    docstring."""
    workers = safe_worker_count(max_workers)
    if workers == 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


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


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | type) -> int:
    """Writes rows to CSV, returns the row count actually written. A caller
    that gets 0 back and expected >0 must decide what that means -- this
    function will not paper over it by skipping the file.

    fieldnames is required and never derived from rows: an empty rows list
    has no first element to derive columns from, so deriving them only in
    the non-empty case produces a real header for a non-empty result and a
    blank line for an empty one -- silently wrong output, not a valid empty
    result (docs/adr/0001-fail-loud-not-silent.md). Pass either the column
    name list directly, or a dataclass type to derive it from via
    dataclasses.fields()."""
    if not fieldnames:
        raise TypeError("write_csv: fieldnames is required -- pass a non-empty column-name list or a dataclass type")
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fn = fieldnames if isinstance(fieldnames, list) else [f.name for f in fields(fieldnames)]
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


def repo_root() -> Path:
    """Walk up from this file to the directory containing pyproject.toml.

    Used to locate vendored, non-Python assets (tools/code-maat.jar) that
    live outside the installed package -- a fixed parent-count breaks the
    moment the package gets nested one level deeper, which is exactly what
    happened when this module moved from chronicle/util.py to
    src/repo_analyser/core/util.py."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root: no pyproject.toml found above core/util.py")
