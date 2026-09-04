"""Test quality: actually execute each repo's unit-test script and record
real pass/fail counts -- not "a test script exists" (a proxy) but "the
suite ran and here is what happened" (the property). Coverage is collected
where the runner supports it out of the box.

Deliberately scoped to *unit* tests only: this portfolio's integration test
scripts (`test:integration:*`) require live AWS/DB/Redis infrastructure this
analysis has no access to, and a network-timeout failure there would be
misreported as a code defect. That scoping is a real limitation, stated
here rather than hidden -- see docs/METHODOLOGY.md.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .lang import detect_repo_language, TESTQUALITY_SUPPORTED
from .util import run, write_csv, write_json

UNIT_SCRIPT_PREFERENCE = ["test:unit", "test"]

def _detect_node20_bin() -> str | None:
    """Best-effort: find a Node 20.x installed via nvm. Override with the
    CHRONICLE_NODE_BIN env var if your setup differs. Returns None (meaning
    "use whatever `node` is already on PATH") if nothing better is found --
    that is recorded per-run via `runtime_node_version`, never assumed."""
    import os
    if os.environ.get("CHRONICLE_NODE_BIN"):
        return os.environ["CHRONICLE_NODE_BIN"]
    nvm_versions = Path.home() / ".nvm" / "versions" / "node"
    if nvm_versions.is_dir():
        candidates = sorted(nvm_versions.glob("v20.*"), reverse=True)
        if candidates:
            return str(candidates[0] / "bin")
    return None


# Why this matters: this portfolio's package.json pins node>=20; if the host
# actually running this tool defaults to a newer major (e.g. v26), a
# transitive dependency of jsonwebtoken (buffer-equal-constant-time) throws
# at require-time -- before any test runs -- purely from the Node version
# mismatch. That is an execution-environment problem, not a defect in the
# analyzed repo, so we pin the Node version used to run suites when we can
# find one, and record which node actually ran otherwise. See METHODOLOGY.md.
NODE20_BIN = _detect_node20_bin()

# vitest's summary line varies by outcome:
#   all passed:        "Tests  12 passed (12)"
#   mixed:             "Tests  3 failed | 9 passed (12)"
#   all failed:        "Tests  1 failed (1)"
# The three real-world formats above were only found by reading raw logs
# where an earlier, narrower regex silently produced 0/0/0 for repos that
# had actually run and failed -- see docs/METHODOLOGY.md.
VITEST_TESTS_LINE_RE = re.compile(
    r"^\s*Tests\s+(?:(?P<failed>\d+)\s+failed)?(?:\s*\|\s*)?(?:(?P<passed>\d+)\s+passed)?\s*\((?P<total>\d+)\)",
    re.MULTILINE,
)
JEST_SUMMARY_RE = re.compile(
    r"Tests:\s+(?:(\d+)\s+failed,\s*)?(?:(\d+)\s+skipped,\s*)?(\d+)\s+passed,\s*(\d+)\s+total",
)
JEST_NO_TESTS_RE = re.compile(r"No tests found, exiting with code 1")
JEST_CONFIG_ERROR_RE = re.compile(r"●\s*Validation Error:")


@dataclass
class TestRunResult:
    repo: str
    script_used: str
    ran: bool
    exit_code: int
    runner_detected: str
    tests_passed: int
    tests_failed: int
    tests_total: int
    duration_s: float
    skip_reason: str = ""
    node_version_used: str = ""
    failure_mode: str = ""


def _pick_script(pkg_scripts: dict) -> str | None:
    for candidate in UNIT_SCRIPT_PREFERENCE:
        if candidate in pkg_scripts:
            return candidate
    return None


def _parse_output(runner: str, text: str) -> tuple[int, int, int, str]:
    """Returns (passed, failed, total, failure_mode). failure_mode is "" for
    a clean parse, else a specific reason so a caller never has to guess
    what an unparsed 0/0/0 actually meant."""
    if runner == "vitest":
        m = VITEST_TESTS_LINE_RE.search(text)
        if m:
            failed = int(m.group("failed") or 0)
            passed = int(m.group("passed") or 0)
            total = int(m.group("total"))
            return passed, failed, total, ""
        return 0, 0, 0, "vitest ran but no 'Tests' summary line found -- see raw log"
    if runner == "jest":
        if JEST_CONFIG_ERROR_RE.search(text):
            return 0, 0, 0, "jest config validation error -- suite never started, see raw log"
        if JEST_NO_TESTS_RE.search(text):
            return 0, 0, 0, "jest ran, testMatch pattern matched zero files -- test infra exists, no tests written"
        m = JEST_SUMMARY_RE.search(text)
        if m:
            failed = int(m.group(1) or 0)
            passed = int(m.group(3) or 0)
            total = int(m.group(4) or 0)
            return passed, failed, total, ""
        return 0, 0, 0, "jest ran but no 'Tests:' summary line found -- see raw log"
    return 0, 0, 0, f"unrecognized runner '{runner}' -- no parser for its output format"


def analyze_repo(repo: Path, timeout: int = 180, log_dir: Path | None = None) -> TestRunResult:
    lang = detect_repo_language(repo)
    if lang == "python":
        return _analyze_python_repo(repo, timeout, log_dir)
    if lang == "go":
        return _analyze_go_repo(repo, timeout, log_dir)
    if lang not in ("javascript", "unknown"):
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0,
                              f"language '{lang}' not supported by testquality (supported: {sorted(TESTQUALITY_SUPPORTED)})")
    return _analyze_js_repo(repo, timeout, log_dir)


PYTEST_SUMMARY_RE = re.compile(
    r"^(?:={3,}\s*)?(?:(?P<failed>\d+)\s+failed,?\s*)?(?:(?P<passed>\d+)\s+passed,?\s*)?"
    r"(?:(?P<skipped>\d+)\s+skipped,?\s*)?(?:(?P<errors>\d+)\s+error[s]?,?\s*)?"
    r"in\s+[\d.]+s",
    re.MULTILINE,
)
PYTEST_NO_TESTS_RE = re.compile(r"no tests ran")


def _pytest_command() -> list[str]:
    """Prefer a bare `pytest` on PATH over `python3 -m pytest`: on a system
    with more than one Python install (pipx, brew, pyenv, ...) `pytest` can
    be on PATH while the specific `python3` resolved has no pytest in its
    own site-packages -- confirmed on the machine this was built on, where
    `python3 -m pytest` failed with ModuleNotFoundError despite a working
    `pytest` binary being installed and on PATH."""
    import shutil
    if shutil.which("pytest"):
        return ["pytest"]
    return ["python3", "-m", "pytest"]


def _analyze_python_repo(repo: Path, timeout: int, log_dir: Path | None) -> TestRunResult:
    has_test_files = any(repo.rglob("test_*.py")) or any(repo.rglob("*_test.py"))
    if not has_test_files:
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no test_*.py / *_test.py files found")

    import time
    t0 = time.time()
    res = run([*_pytest_command(), "--tb=no", "-q"], cwd=repo, check=False, timeout=timeout)
    duration = round(time.time() - t0, 1)
    combined = res.stdout + "\n" + res.stderr
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"{repo.name}.log").write_text(combined)

    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                              failure_mode="import error before tests ran -- likely missing dependency install, see raw log")
    if PYTEST_NO_TESTS_RE.search(combined):
        return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                              failure_mode="pytest ran, collected zero tests")
    m = PYTEST_SUMMARY_RE.search(combined)
    if not m:
        return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                              failure_mode="pytest ran but no summary line found -- see raw log")
    passed = int(m.group("passed") or 0)
    failed = int(m.group("failed") or 0) + int(m.group("errors") or 0)
    total = passed + failed + int(m.group("skipped") or 0)
    return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", passed, failed, total, duration)


def _analyze_go_repo(repo: Path, timeout: int, log_dir: Path | None) -> TestRunResult:
    if not (repo / "go.mod").exists():
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no go.mod found")
    if not any(repo.rglob("*_test.go")):
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no *_test.go files found")

    import time
    t0 = time.time()
    res = run(["go", "test", "-json", "./..."], cwd=repo, check=False, timeout=timeout)
    duration = round(time.time() - t0, 1)
    combined = res.stdout + "\n" + res.stderr
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"{repo.name}.log").write_text(combined)

    passed = failed = 0
    saw_any_event = False
    for line in res.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        # go test -json emits one event per line; a completed *test* (not
        # package-level) has both "Test" and a terminal "Action" of pass/fail/skip.
        if event.get("Test") and event.get("Action") in ("pass", "fail"):
            saw_any_event = True
            if event["Action"] == "pass":
                passed += 1
            else:
                failed += 1
    if not saw_any_event:
        if "cannot find package" in combined or "no required module" in combined:
            return TestRunResult(repo.name, "go test", True, res.returncode, "go test", 0, 0, 0, duration,
                                  failure_mode="`go test` could not resolve dependencies -- see raw log")
        return TestRunResult(repo.name, "go test", True, res.returncode, "go test", 0, 0, 0, duration,
                              failure_mode="go test ran but produced no parseable test events -- see raw log")
    return TestRunResult(repo.name, "go test", True, res.returncode, "go test", passed, failed, passed + failed, duration)


def _analyze_js_repo(repo: Path, timeout: int, log_dir: Path | None) -> TestRunResult:
    pkg_path = repo / "package.json"
    if not pkg_path.exists():
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no package.json")
    pkg = json.loads(pkg_path.read_text())
    scripts = pkg.get("scripts", {})
    script = _pick_script(scripts)
    if not script:
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no unit-test script in package.json")
    if not (repo / "node_modules").is_dir():
        return TestRunResult(repo.name, script, False, -1, "", 0, 0, 0, 0.0, "no node_modules (npm install failed)")

    script_body = scripts[script]
    runner = "vitest" if "vitest" in script_body else "jest" if "jest" in script_body else "unknown"

    import time
    node_ver_res = run(["node", "--version"], check=False, extra_path=NODE20_BIN)
    node_version = node_ver_res.stdout.strip() or "unknown"

    t0 = time.time()
    res = run(["npm", "run", script, "--silent"], cwd=repo, check=False, timeout=timeout, extra_path=NODE20_BIN)
    duration = round(time.time() - t0, 1)
    combined = res.stdout + "\n" + res.stderr
    passed, failed, total, failure_mode = _parse_output(runner, combined)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"{repo.name}.log").write_text(combined)
    return TestRunResult(
        repo=repo.name, script_used=script, ran=True, exit_code=res.returncode,
        runner_detected=runner, tests_passed=passed, tests_failed=failed, tests_total=total,
        duration_s=duration, node_version_used=node_version, failure_mode=failure_mode,
    )


def run_testquality(repos: list[Path], out_dir: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in repos:
        result = analyze_repo(r, log_dir=tmp_dir)
        rows.append(asdict(result))
    out_path = out_dir / "testquality_runs.csv"
    write_csv(out_path, rows)

    ran = [r for r in rows if r["ran"]]
    real_failures = [r for r in ran if r["tests_failed"] > 0]
    zero_tests_written = [r for r in ran if r["failure_mode"].startswith("jest ran, testMatch")]
    config_broken = [r for r in ran if "config" in r["failure_mode"]]
    write_json(out_dir / "testquality_summary.json", {
        "total_repos": len(repos),
        "repos_with_unit_script": len(ran),
        "repos_all_tests_passing": sum(1 for r in ran if r["exit_code"] == 0 and r["tests_total"] > 0),
        "repos_with_real_test_failures_right_now": len(real_failures),
        "repos_with_real_test_failures_list": [r["repo"] for r in real_failures],
        "repos_with_test_infra_but_zero_tests_written": len(zero_tests_written),
        "repos_with_test_infra_but_zero_tests_written_list": [r["repo"] for r in zero_tests_written],
        "repos_with_broken_test_config": len(config_broken),
        "repos_with_broken_test_config_list": [r["repo"] for r in config_broken],
        "repos_skipped_no_script": sum(1 for r in rows if not r["ran"]),
        "skip_reasons": {r["repo"]: r["skip_reason"] for r in rows if not r["ran"]},
    })
    return out_path
