"""Python dead-code detection via vulture -- a pure-AST static analyzer
(confirmed via `vulture --help` and direct execution: it only reads
file/dir paths, never imports/executes target-repo code, so it needs zero
installed dependencies from the target repo -- unlike depgraph.py's
node_modules requirement for dependency-cruiser).

No --min-confidence override: no other collector here has an established
confidence-threshold convention, and vulture's default (60%) is what
surfaces unused functions/classes/methods -- ruff already reports unused
imports (F401) via lint_quality.py, so a high-confidence-only filter would
just re-report what ruff covers and hide the one thing vulture adds.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from ...core.util import run
from .models import Finding

VULTURE_TIMEOUT_S = 120  # same class of tool as lint_quality.py's ruff call
                          # (fast, AST-based) -- no need for jscpd's larger budget.

# e.g. "src/app.py:12: unused function 'helper' (60% confidence)" --
# verified against a real, installed vulture 2.16, not guessed. Vulture's
# other line shape ("unreachable code after 'return' (100% confidence)")
# has no unused *name*, so it doesn't match and is silently skipped -- same
# as any other non-matching line (e.g. a syntax-error line vulture prints
# for one malformed file while it keeps scanning the rest of the repo:
# confirmed directly, vulture already degrades per-file on its own).
VULTURE_LINE_RE = re.compile(
    r"^(?P<file>.+):(?P<line>\d+): unused (?P<kind>\S+) '(?P<name>[^']+)' \(\d+% confidence\)\s*$"
)


def vulture_available() -> bool:
    return shutil.which("vulture") is not None


def has_python_files(repo: Path) -> bool:
    return any(
        p.is_file() and p.suffix == ".py" and not any(part in EXCLUDE_DIR_PARTS for part in p.parts)
        for p in repo.rglob("*")
    )


def _to_repo_relative(file_str: str, repo: Path) -> str:
    try:
        return str(Path(file_str).resolve().relative_to(repo.resolve()))
    except ValueError:
        return file_str  # outside repo somehow -- keep vulture's own path rather than crash


def parse_vulture_stdout(stdout: str, repo: Path) -> list[Finding]:
    """Pure parsing, no subprocess -- kept separate from run_vulture so the
    parsing contract can be unit-tested against a known-real string without
    needing vulture installed on the test machine."""
    findings = []
    for line in stdout.splitlines():
        m = VULTURE_LINE_RE.match(line)
        if not m:
            continue
        findings.append(Finding(
            language="python", kind=m.group("kind"),
            file=_to_repo_relative(m.group("file"), repo),
            line=int(m.group("line")), name=m.group("name"),
        ))
    return findings


def run_vulture(repo: Path) -> list[Finding]:
    """Runs vulture against the whole repo tree. Vulture itself exits 3
    when it finds unused code and 1 on a usage/parse error -- neither is
    "the tool failed" here (check=False); only a raised exception from
    `run` itself (timeout, missing binary despite the earlier PATH check --
    a rare TOCTOU race) is the caller's problem to catch.

    --exclude matters: unlike ruff, vulture has no built-in vendor-dir
    defaults, so without it a physically-present `.venv`/`node_modules`
    inside the repo tree gets scanned too -- caught empirically, a real
    self-run over this repo returned 7144 findings before this fix, almost
    all from `.venv/lib/.../_pytest/`. Reuses EXCLUDE_DIR_PARTS so vulture's
    scan matches has_python_files' own tree walk.

    Patterns are `*/name/*`, not the bare name: vulture matches a
    wildcard-free pattern as `*name*` against the *whole absolute path*
    (its own --help), which is a substring match, not a path-segment
    match -- a bare "vendor" would also match an unrelated path that merely
    contains that substring (caught empirically: a pytest tmp_path named
    after this very test, "test_vendored_...", tripped it). Anchoring with
    slashes restricts each pattern to an actual directory named exactly
    `name` in the path, matching EXCLUDE_DIR_PARTS' own `part in p.parts`
    semantics elsewhere in this collector."""
    exclude = ",".join(f"*/{name}/*" for name in sorted(EXCLUDE_DIR_PARTS))
    res = run(["vulture", str(repo), "--exclude", exclude], check=False, timeout=VULTURE_TIMEOUT_S)
    return parse_vulture_stdout(res.stdout, repo)
