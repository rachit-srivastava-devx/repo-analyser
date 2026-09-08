"""Doc-comment coverage, Python: `interrogate` (confirmed via `interrogate
--help` -- there is no JSON/machine-parseable output flag, only a single-
line text summary in default verbosity: "RESULT: PASSED (minimum: 0.0%,
actual: 62.5%)"). Run with `--fail-under 0` so the process always exits 0
on a real measurement (interrogate's own default --fail-under is 80.0,
which would otherwise make a merely-mediocre-but-real 50% coverage look
like a tool failure) and the same `core.lang.EXCLUDE_DIR_PARTS` every
other collector already uses, passed as repeated `--exclude` flags, so a
committed `vendor/`/`build/` tree of someone else's code doesn't dilute
this repo's own coverage number (confirmed live: interrogate skips
dot-directories like `.venv` on its own, but walks plain `vendor/`/
`build/` unless told not to)."""
from __future__ import annotations

import shutil
from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from ...core.util import run
from .models import INTERROGATE_NO_FILES_MARKER, INTERROGATE_RESULT_RE


def _python_doc_coverage(repo: Path) -> tuple[float, str, str]:
    """Returns (coverage_pct, tool, skip_reason) for a Python repo."""
    if not shutil.which("interrogate"):
        return 0.0, "", "interrogate not on PATH"

    cmd = ["interrogate", "--no-color", "--fail-under", "0"]
    for d in sorted(EXCLUDE_DIR_PARTS):
        cmd += ["--exclude", d]
    cmd.append(".")
    # check=False: a repo with zero Python files (e.g. every .py lives under
    # an excluded vendor dir) makes interrogate itself exit 1 with a plain,
    # recognizable stderr message -- a legitimate empty result, not a tool
    # failure, so it must not raise here.
    res = run(cmd, cwd=repo, check=False, timeout=120)

    m = INTERROGATE_RESULT_RE.search(res.stdout)
    if m:
        return float(m.group(1)), "interrogate", ""
    if INTERROGATE_NO_FILES_MARKER in res.stderr:
        return 0.0, "", "no Python files found by interrogate"
    # Confirmed live: a single file with a genuine syntax error anywhere in
    # the tree makes interrogate crash with an uncaught traceback (exit 1)
    # instead of skipping just that file -- this is interrogate's own
    # behavior, not a bug in this module. Reported as an explicit
    # skip_reason (matching lint_quality.py's own "unparseable output"
    # precedent) rather than either a fabricated 0.0 or letting the
    # traceback text corrupt this repo's CSV row.
    detail = (res.stderr or res.stdout).strip().splitlines()
    return 0.0, "", f"interrogate produced unparseable output: {(detail[-1] if detail else '(empty)')[:300]}"
