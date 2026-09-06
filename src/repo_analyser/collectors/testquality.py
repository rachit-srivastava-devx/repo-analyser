"""Test quality: actually execute each repo's unit-test script and record
real pass/fail counts -- not "a test script exists" (a proxy) but "the
suite ran and here is what happened" (the property). Coverage is not
collected today -- see docs/METHODOLOGY.md.

Deliberately scoped to *unit* tests only: this portfolio's integration test
scripts (`test:integration:*`) require live AWS/DB/Redis infrastructure this
analysis has no access to, and a network-timeout failure there would be
misreported as a code defect. That scoping is a real limitation, stated
here rather than hidden -- see docs/METHODOLOGY.md.
"""
from __future__ import annotations

import json
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.lang import TESTQUALITY_SUPPORTED, detect_js_test_runner, detect_repo_language, pick_unit_script
from ..core.util import run, write_csv, write_json


def _detect_node20_bin() -> str | None:
    """Best-effort: find a Node 20.x installed via nvm. Override with the
    REPO_ANALYSER_NODE_BIN env var if your setup differs. Returns None (meaning
    "use whatever `node` is already on PATH") if nothing better is found --
    that is recorded per-run via `runtime_node_version`, never assumed."""
    import os
    if os.environ.get("REPO_ANALYSER_NODE_BIN"):
        return os.environ["REPO_ANALYSER_NODE_BIN"]
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
        reason = f"language '{lang}' not supported by testquality (supported: {sorted(TESTQUALITY_SUPPORTED)})"
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, reason)
    return _analyze_js_repo(repo, timeout, log_dir)


# Real regex-scraping of pytest's human-readable text summary used to live
# here (PYTEST_SUMMARY_RE / PYTEST_NO_TESTS_RE / PYTEST_COLLECTION_ERROR_RE)
# -- three separate patterns, one of which existed specifically to patch
# around a real miscount bug the others caused (a collection error's "N
# error(s) during collection" line matched the generic summary regex's
# `errors` group, reporting a collection failure as "1 failed, 1 total").
# pytest ships a stable, structured alternative to all of this:
# `--junit-xml`, which reports `errors`/`failures`/`tests`/`skipped` as
# actual XML attributes -- the exact distinction the collection-error regex
# existed to reconstruct by pattern-matching prose, given for free. Parsed
# below with stdlib `xml.etree.ElementTree`; no new dependency needed for a
# schema this simple.


def _pytest_command(repo: Path) -> list[str]:
    """Prefer the target repo's own virtualenv pytest over a bare `pytest`
    on PATH -- same principle as lint_quality.py using each repo's own
    node_modules/.bin/eslint rather than npx: a bare `pytest` on PATH may
    belong to a *different* Python environment than the one the target
    repo's own tests need, which produces a real collection-time
    ImportError that has nothing to do with the target repo's actual test
    health. Caught by dogfooding this tool on itself: analyzing this very
    repo without its .venv preferred reported errors=19 in the junit-xml
    (every test file failing to import `repo_analyser`) -- correctly
    *not* miscounted as 19 failed tests (see `_parse_junit_xml` above),
    but still a false "no tests could run" for a repo whose tests
    demonstrably do run under its own venv.

    Falls back to a bare `pytest` on PATH (on a system with more than one
    Python install, `pytest` can be on PATH while the specific `python3`
    resolved has no pytest in its own site-packages -- confirmed on the
    machine this was built on), then to `python3 -m pytest`."""
    import shutil
    for venv_dir in (".venv", "venv"):
        venv_pytest = repo / venv_dir / "bin" / "pytest"
        if venv_pytest.is_file():
            return [str(venv_pytest)]
    if shutil.which("pytest"):
        return ["pytest"]
    return ["python3", "-m", "pytest"]


def _parse_junit_xml(xml_path: Path) -> tuple[int, int, int, int]:
    """Returns (passed, failed, total, errors). `failed` folds in `errors`
    (a fixture/collection error is not a confirmed-working test either,
    same practical meaning to a report reader) -- `errors` is also
    returned on its own so the caller can distinguish "every counted test
    was actually a collection error" from a genuine mixed run."""
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return 0, 0, 0, 0
    total = int(suite.get("tests", 0))
    errors = int(suite.get("errors", 0))
    failures = int(suite.get("failures", 0))
    skipped = int(suite.get("skipped", 0))
    passed = max(0, total - errors - failures - skipped)
    return passed, failures + errors, total, errors


def _analyze_python_repo(repo: Path, timeout: int, log_dir: Path | None) -> TestRunResult:
    has_test_files = any(repo.rglob("test_*.py")) or any(repo.rglob("*_test.py"))
    if not has_test_files:
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no test_*.py / *_test.py files found")

    import time
    with tempfile.TemporaryDirectory() as tmp:
        junit_path = Path(tmp) / "junit.xml"
        t0 = time.time()
        res = run([*_pytest_command(repo), f"--junit-xml={junit_path}", "--tb=no", "-q"],
                   cwd=repo, check=False, timeout=timeout)
        duration = round(time.time() - t0, 1)
        combined = res.stdout + "\n" + res.stderr
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{repo.name}.log").write_text(combined)

        if not junit_path.exists():
            return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                                  failure_mode=f"pytest produced no junit-xml report -- see raw log: "
                                               f"{combined[-500:]}")
        passed, failed, total, errors = _parse_junit_xml(junit_path)

    if total == 0:
        return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                              failure_mode="pytest ran, collected zero tests")
    if errors > 0 and passed == 0 and failed == errors:
        # every counted "test" is an error (collection/fixture failure),
        # not a real executed pass/fail -- distinguishable from a mixed
        # run because the XML gives errors/failures as separate counts,
        # not a single ambiguous number reconstructed from prose.
        return TestRunResult(repo.name, "pytest", True, res.returncode, "pytest", 0, 0, 0, duration,
                              failure_mode="import error before tests ran -- likely missing dependency "
                                            "install, see raw log")
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
    return TestRunResult(repo.name, "go test", True, res.returncode, "go test",
                          passed, failed, passed + failed, duration)


def _analyze_js_repo(repo: Path, timeout: int, log_dir: Path | None) -> TestRunResult:
    pkg_path = repo / "package.json"
    if not pkg_path.exists():
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no package.json")
    pkg = json.loads(pkg_path.read_text())
    scripts = pkg.get("scripts", {})
    script = pick_unit_script(scripts)
    if not script:
        return TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, "no unit-test script in package.json")
    if not (repo / "node_modules").is_dir():
        return TestRunResult(repo.name, script, False, -1, "", 0, 0, 0, 0.0, "no node_modules (npm install failed)")

    script_body = scripts[script]
    runner = detect_js_test_runner(script_body)

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
