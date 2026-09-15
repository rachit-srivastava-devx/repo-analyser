"""Test quality: actually execute each repo's unit-test script and record
real pass/fail counts -- not "a test script exists" (a proxy) but "the
suite ran and here is what happened" (the property). Coverage is not
collected today -- see docs/METHODOLOGY.md.

Deliberately scoped to *unit* tests only: this portfolio's integration test
scripts (`test:integration:*`) require live AWS/DB/Redis infrastructure this
analysis has no access to, and a network-timeout failure there would be
misreported as a code defect. That scoping is a real limitation, stated
here rather than hidden -- see docs/METHODOLOGY.md.

Also reports three static signals that are NOT scoped to unit-only, since
they answer a different, repo-wide question (what test *shape* exists,
not whether the unit suite passed): test-pyramid shape (unit/integration/
e2e/unclassified file counts, by directory-name heuristic -- see
_pyramid_tier), fuzz/property-based test *usage* (hypothesis/fast-check/
Go-native-fuzz -- a real import-plus-invocation check in the same file,
not a manifest-presence proxy; see _fuzz_signal's own docstring for why
that distinction was tightened 2026-09-14), and snapshot-test overuse
(`.snap` file count plus a git-churn proxy for how often they get
regenerated). All three are filesystem/git-history checks, computed the
same way regardless of whether the unit-test execution above ran,
skipped, or failed -- see _static_test_signals.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TypedDict

import defusedxml.ElementTree as ET

from ..core.lang import (
    EXCLUDE_DIR_PARTS,
    TEST_FILE_RE,
    TESTQUALITY_SUPPORTED,
    detect_js_test_runner,
    detect_repo_language,
    pick_unit_script,
)
from ..core.util import is_git_repo, run, write_csv, write_json


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
    # Test-pyramid shape, fuzz/property-test presence, and snapshot-test
    # overuse -- see _static_test_signals below. Computed the same way
    # regardless of ran/skip_reason above: these are filesystem/git-history
    # questions, not part of the test *execution* result, so a repo that
    # skipped execution entirely still gets a real answer here.
    pyramid_unit_files: int = 0
    pyramid_integration_files: int = 0
    pyramid_e2e_files: int = 0
    pyramid_unclassified_files: int = 0
    has_fuzz_tests: bool = False
    fuzz_tools: str = ""
    snapshot_file_count: int = 0
    snapshot_churn_commits: int = 0
    snapshot_churn_note: str = ""


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
        result = _analyze_python_repo(repo, timeout, log_dir)
    elif lang == "go":
        result = _analyze_go_repo(repo, timeout, log_dir)
    elif lang not in ("javascript", "unknown"):
        reason = f"language '{lang}' not supported by testquality (supported: {sorted(TESTQUALITY_SUPPORTED)})"
        result = TestRunResult(repo.name, "", False, -1, "", 0, 0, 0, 0.0, reason)
    else:
        result = _analyze_js_repo(repo, timeout, log_dir)
    # Pyramid/fuzz/snapshot signals are independent of which branch above
    # ran (or skipped) -- a static filesystem+git scan, not a re-run of the
    # suite -- so they're attached uniformly to every row, including the
    # early-return skip_reason rows constructed above.
    return replace(result, **_static_test_signals(repo))


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
# below with `defusedxml.ElementTree` (drop-in `parse()` for stdlib's
# `xml.etree.ElementTree`, XXE-hardened) rather than the stdlib module --
# semgrep correctly flagged the stdlib module here: this junit.xml is
# pytest's own output, but pytest is running the TARGET REPO's test suite,
# and this tool's whole security model (see README) treats target-repo
# content as untrusted. A crafted test name/docstring surviving into the
# report unescaped by a pytest XML-escaping bug is a thin, indirect vector,
# but the fix costs nothing (defusedxml has no transitive deps and needs no
# network/credential) so there's no reason to accept even a remote risk.


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


# --- Test-pyramid shape --------------------------------------------------
# Directory-name heuristic ONLY, layered on top of TEST_FILE_RE's own
# already-approximate file-naming match -- explicitly NOT ground truth.
# Plenty of real repos don't name test directories this way at all (a flat
# tests/ dir with no tier subfolders, or a framework convention like
# cypress/e2e/ that TEST_FILE_RE itself doesn't even match -- see that
# regex's own definition in core/lang.py). Every TEST_FILE_RE match gets a
# bucket, including "unclassified" -- never silently dropped, and never
# forced into unit/integration/e2e by default, which would be a *worse*
# lie than an honest "don't know" bucket.
PYRAMID_UNIT_SEGMENTS = {"unit", "units"}
PYRAMID_INTEGRATION_SEGMENTS = {"integration", "integrations"}
PYRAMID_E2E_SEGMENTS = {"e2e", "e2e-tests", "e2e_tests", "end2end", "end-to-end"}


def _pyramid_tier(rel_posix_path: str) -> str:
    """Which pyramid tier a TEST_FILE_RE-matched path belongs to, by
    directory name alone. Scans directory segments closest-to-the-file
    first, so a path naming more than one tier (e.g.
    "tests/integration/e2e/foo.spec.ts") resolves to the more specific,
    innermost label ("e2e") rather than the broader outer grouping -- the
    file itself, not its parent's parent, is what the path is actually
    claiming. Falls back to "unclassified" -- a real, expected bucket for a
    repo that names test directories some other way entirely (or not at
    all), not an error."""
    segments = [s.lower() for s in rel_posix_path.split("/")[:-1]]
    for segment in reversed(segments):
        if segment in PYRAMID_UNIT_SEGMENTS:
            return "unit"
        if segment in PYRAMID_INTEGRATION_SEGMENTS:
            return "integration"
        if segment in PYRAMID_E2E_SEGMENTS:
            return "e2e"
    return "unclassified"


def _scan_test_files_and_snapshots(repo: Path) -> tuple[dict[str, int], int]:
    """One tree walk answering two independent per-file questions -- test-
    pyramid tier for every TEST_FILE_RE match, and how many .snap files
    exist -- rather than walking a possibly-50k-file tree twice for two
    unrelated but equally cheap per-file checks. Same exclude-list and walk
    shape as detect_repo_language (core/lang.py), so a huge repo's
    node_modules/vendor/build noise is skipped here exactly like it is
    everywhere else in this codebase."""
    pyramid = {"unit": 0, "integration": 0, "e2e": 0, "unclassified": 0}
    snapshot_files = 0
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        rel = p.relative_to(repo).as_posix()
        if TEST_FILE_RE.search(rel):
            pyramid[_pyramid_tier(rel)] += 1
        if p.suffix == ".snap":
            snapshot_files += 1
    return pyramid, snapshot_files


# --- Fuzz / property-based test usage -------------------------------------
# Real usage, not manifest presence: independent adversarial verification
# (2026-09-14) found the original Python/JS checks here were a dependency-
# manifest grep -- a repo with `hypothesis` listed in requirements.txt but
# never imported or invoked anywhere reported identically to a repo with a
# real @given-decorated property test, under a field name (has_fuzz_tests)
# that plainly claims tests exist. That's the exact "proxy for the
# property" drift this repo's own AGENTS.md names by name ("'osv-scanner
# ran' reported as 'no vulnerabilities'") -- Go's branch below never had
# this problem, since Go's own native-fuzzing convention has no separate
# manifest step to begin with, only a function signature to grep for. All
# three ecosystems now require the same standard of evidence: an actual
# import AND an actual invocation of the fuzzing construct, in the same
# file -- still not a check that any fuzz target actually runs or finds
# anything (that would be real subprocess execution, out of scope here per
# the roadmap's own wording), but no longer confusable with an unused
# dependency line. See docs/METHODOLOGY.md for the full before/after.
HYPOTHESIS_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+hypothesis(?:\.\w+)*\s+import\b|import\s+hypothesis\b)", re.MULTILINE
)
HYPOTHESIS_GIVEN_USAGE_RE = re.compile(r"@(?:hypothesis\.)?given\s*\(")
# fast-check's own documented usage shape is `<binding>.assert(<binding>.property(...))`;
# the import line's bound name is captured (not hardcoded to "fc", though
# that's the near-universal convention in fast-check's own docs) so a
# renamed import is still matched correctly.
FAST_CHECK_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+(?:\*\s+as\s+)?(\w+)\s+from\s+['\"]fast-check['\"]"
    r"|const\s+(\w+)\s*=\s*require\(\s*['\"]fast-check['\"]\s*\))",
    re.MULTILINE,
)
FAST_CHECK_JS_SUFFIXES = (".js", ".jsx", ".ts", ".tsx")
# Go's own native fuzzing (1.18+) needs no dependency at all -- the signal
# is a function *signature* convention (name prefix + the testing.F
# parameter type), not a manifest entry. Requiring the *testing.F parameter
# (not just a "func Fuzz..." name prefix) rules out an unrelated function
# that merely happens to start with "Fuzz" (e.g. "func FuzzyMatch(s
# string) bool") from being counted.
GO_FUZZ_FUNC_RE = re.compile(r"\bfunc\s+Fuzz\w*\s*\(\s*\w+\s+\*testing\.F\s*\)")


def _python_uses_hypothesis(repo: Path) -> bool:
    """Requires both a real `from hypothesis import ...`/`import hypothesis`
    line AND an actual `@given(...)` (or `@hypothesis.given(...)`) decorator
    usage, in the SAME file -- mirrors _go_uses_native_fuzz's own
    same-file, same-construct convention below. Scoped to TEST_FILE_RE-
    matching .py files, since that's where a real property-based test
    actually lives; a manifest-only mention with no matching test file is
    exactly the "declared but never used" case this check now excludes."""
    for p in repo.rglob("*.py"):
        if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        rel = p.relative_to(repo).as_posix()
        if not TEST_FILE_RE.search(rel):
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if HYPOTHESIS_IMPORT_RE.search(text) and HYPOTHESIS_GIVEN_USAGE_RE.search(text):
            return True
    return False


def _js_uses_fast_check(repo: Path) -> bool:
    """Requires a real `import ... from 'fast-check'` (or `require(...)`)
    binding AND both `.property(` and `.assert(` called on that same
    binding, in the SAME file -- same "declared but never used" exclusion
    as _python_uses_hypothesis above. Scoped to TEST_FILE_RE-matching
    .js/.jsx/.ts/.tsx files."""
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.suffix not in FAST_CHECK_JS_SUFFIXES:
            continue
        rel = p.relative_to(repo).as_posix()
        if not TEST_FILE_RE.search(rel):
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        m = FAST_CHECK_IMPORT_RE.search(text)
        if not m:
            continue
        binding = re.escape(m.group(1) or m.group(2))
        if (re.search(rf"\b{binding}\.assert\s*\(", text)
                and re.search(rf"\b{binding}\.property\s*\(", text)):
            return True
    return False


def _go_uses_native_fuzz(repo: Path) -> bool:
    """Scoped to *_test.go files only -- the only place Go's own tooling
    will ever recognize a fuzz target -- consistent with
    _analyze_go_repo's own *_test.go enumeration above."""
    for p in repo.rglob("*_test.go"):
        if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if GO_FUZZ_FUNC_RE.search(text):
            return True
    return False


def _fuzz_signal(repo: Path) -> tuple[bool, str]:
    """Checked across all three ecosystems regardless of the repo's own
    detect_repo_language() dominant-language verdict -- a JS-dominant
    monorepo with a Python backend using hypothesis is a real, if
    uncommon, case this should still answer honestly rather than only
    checking whichever language happens to have the most files."""
    tools = []
    if _python_uses_hypothesis(repo):
        tools.append("hypothesis")
    if _js_uses_fast_check(repo):
        tools.append("fast-check")
    if _go_uses_native_fuzz(repo):
        tools.append("go-native-fuzz")
    return bool(tools), ";".join(tools)


# --- Snapshot-test overuse ------------------------------------------------
# Both numbers below are named, explicitly, as crude proxies -- per
# docs/checklist-by-repo-type's own framing of snapshot tests as prone to
# being "rubber-stamped" (--update-snapshots on a real behavior change
# looks identical, in these counts, to the same command rubber-stamping an
# actual regression). Neither number can tell those two apart; that is a
# real, stated limitation of what a static/history scan can answer, not
# something a smarter regex would fix.
def _snapshot_churn_commits(repo: Path, timeout: int = 60) -> tuple[int, str]:
    """Commit-count proxy for "how often do snapshot files get
    regenerated" -- equivalent to
    `git log --follow --oneline -- '*.snap' | wc -l` (docs/ROADMAP.md).
    core.util.run() never shells out through a pipe (AGENTS.md: no
    shell=True, ever), so the line-count is done natively on captured
    stdout instead, which is exactly equivalent.

    Returns (count, note). note is "" for an ordinary result -- including a
    healthy repo that has simply never touched a .snap file, and a real
    git repo with zero .snap files in history, both of which are real
    zeros, not failures. count is -1 (never a bare 0, which would look
    identical to a confirmed empty result) only when git itself could not
    answer the question at all; note then explains why."""
    if not is_git_repo(repo):
        return 0, "not a git repository"
    try:
        res = run(["git", "log", "--follow", "--oneline", "--", "*.snap"],
                   cwd=repo, check=False, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return -1, f"git log could not run: {e}"
    if res.returncode == 0:
        return len(res.stdout.splitlines()), ""
    # A repo with zero commits at all (unborn HEAD) is a real, valid input
    # (AGENTS.md's edge-case ladder, rung 1: "zero commits") -- git itself
    # reports this as a non-zero exit with a specific, recognized message
    # rather than an empty log, so it's distinguished here from a genuine,
    # undiagnosed git failure instead of being folded into the -1 case.
    if "does not have any commits yet" in res.stderr or "bad default revision" in res.stderr:
        return 0, "repo has zero commits"
    return -1, f"git log failed ({res.returncode}): {res.stderr.strip()[:200]}"


class _StaticTestSignals(TypedDict):
    pyramid_unit_files: int
    pyramid_integration_files: int
    pyramid_e2e_files: int
    pyramid_unclassified_files: int
    has_fuzz_tests: bool
    fuzz_tools: str
    snapshot_file_count: int
    snapshot_churn_commits: int
    snapshot_churn_note: str


def _static_test_signals(repo: Path) -> _StaticTestSignals:
    """Test-pyramid shape, fuzz/property-test presence, and snapshot-test
    overuse (docs/ROADMAP.md's testquality.py extension bullet). Computed
    independently of which language branch analyze_repo took -- these are
    filesystem/git-history questions, not a test *execution* result, so
    even a repo analyze_repo otherwise skips entirely (wrong language, no
    unit-test script, no node_modules, ...) still gets a real, non-
    fabricated answer here: none of these three questions depend on being
    able to actually run the suite, only on what's committed."""
    pyramid, snapshot_files = _scan_test_files_and_snapshots(repo)
    has_fuzz, fuzz_tools = _fuzz_signal(repo)
    churn, churn_note = _snapshot_churn_commits(repo)
    return {
        "pyramid_unit_files": pyramid["unit"],
        "pyramid_integration_files": pyramid["integration"],
        "pyramid_e2e_files": pyramid["e2e"],
        "pyramid_unclassified_files": pyramid["unclassified"],
        "has_fuzz_tests": has_fuzz,
        "fuzz_tools": fuzz_tools,
        "snapshot_file_count": snapshot_files,
        "snapshot_churn_commits": churn,
        "snapshot_churn_note": churn_note,
    }


def run_testquality(repos: list[Path], out_dir: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in repos:
        result = analyze_repo(r, log_dir=tmp_dir)
        rows.append(asdict(result))
    out_path = out_dir / "testquality_runs.csv"
    write_csv(out_path, rows, fieldnames=TestRunResult)

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
