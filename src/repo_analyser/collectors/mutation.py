"""Mutation testing: injects synthetic bugs and checks whether the test
suite actually catches them -- the real answer to "is test coverage
meaningful," which passing-test-count alone cannot answer (a file can have
passing tests that assert nothing that would catch a real defect; see
docs/METHODOLOGY.md for a real example this tool found).

Two backends, dispatched by language (see core.lang.MUTATION_SUPPORTED):
Stryker for JS/TS, mutmut for Python. Both are scoped deliberately, not
exhaustively: only repos with a fully-passing unit suite (testquality.py's
output) should be mutated -- a failing suite has no meaningful mutation-score
baseline -- and only the repo's single highest complexity x churn hotspot
(complexity.py's output) is mutated, not the whole codebase, to keep runtime
bounded.

Stryker recipe (JS/TS) -- hard-won, three earlier attempts documented in
docs/METHODOLOGY.md failed on npx package isolation, a missing typescript
peer resolution, and a stale cached binary name collision:
  1. Real local install (`npm install --no-save`, not `npx`) with
     `--legacy-peer-deps` (Stryker's own peer deps routinely conflict with
     a project's pinned eslint/typescript versions).
  2. Invoke the installed `node_modules/.bin/stryker` binary directly, not
     `npx stryker` (npx can resolve a stale/wrong cached package under
     that exact bin name).
  3. Pass through the project's own `jest.config.js` via Stryker's
     `jest.configFile` option, AND set whatever environment variable that
     config needs to select its unit-test testMatch pattern (this
     portfolio's jest configs gate `testMatch` on `TEST_TYPE=unit`; a
     config that conditions its test pattern on an env var will report
     "no tests found" otherwise, not an error naming the real cause).

mutmut recipe (Python, v3.3.1's real CLI, grounded against its installed
source at `mutmut/__main__.py`, not guessed):
  1. mutmut reads config from a `[mutmut]` section in `setup.cfg` (v3.3.1
     has no `--config`/`--paths-to-mutate` flag on `mutmut run` itself) --
     write one temporarily into the target repo, restore/remove it
     afterward so a real run never leaves the target repo's tree changed.
  2. `mutmut run` then `mutmut results --all true`. Grounded against the
     installed 3.7.0 (up from 3.3.1, a real version drift caught by this
     tool's own real-execution test suite going red -- see
     docs/METHODOLOGY.md #24): plain `mutmut results` now prints nothing
     by default in this version (only non-default statuses, apparently,
     though none showed even for a killed mutant in a from-scratch run);
     `--all true` is required to get the full per-mutant listing at all.
     The line format itself (`<qualified_name>: <status>`, arbitrary
     leading whitespace) is unchanged from 3.3.1.
  3. `mutmut results` prints one `<qualified_name>: <status>` line per
     mutant. The status vocabulary is mutmut's own -- killed, survived,
     timeout, suspicious, skipped, "no tests", segfault -- read directly
     from `status_by_exit_code` in its source, not inferred from a sample.
  4. This same fork-unsafety crash escalated, for real, to a kernel panic
     that took down the whole host during the first full-portfolio run
     (2026-09-04) -- not a contained per-mutant labeling quirk. mutmut's
     own dependency `setproctitle` calls into CoreFoundation from the
     child side of `fork()`, before `exec()`; that is unsafe whenever the
     parent is multithreaded (exactly why CPython's own `multiprocessing`
     defaults macOS to `spawn` instead of `fork`), and this tool's parent
     process (a Claude Code session) qualifies. One crashing worker is a
     `segfault` status row; enough of them crash-looping in the same
     180s window starved the host badly enough that `watchdogd` couldn't
     check in for 91 seconds and the kernel force-panicked as a last
     resort -- confirmed from the actual panic log, not inferred. mutmut
     >=3.7.0 defaults `use_setproctitle` to False on Darwin already
     (boxed/mutmut#450), but that default depends on which mutmut version
     happens to be resolved on PATH at run time, so `_mutmut_setup_cfg_text`
     below forces it explicitly rather than trusting that. `segfault` is
     still tracked as its own real status (never folded into "survived"
     or "killed"), but a nonzero count post-fix should be rare and worth
     investigating rather than expected -- see docs/METHODOLOGY.md #18/#23.

Stryker recipe, point 3 correction (docs/METHODOLOGY.md #26/#27): the
`jest.configFile` handling above was real, but `testRunner` was hardcoded
to `"jest"` unconditionally and the `TEST_TYPE`-gating env var was written
under the wrong key (`{"unit": "unit"}` instead of `{"TEST_TYPE": "unit"}`)
-- so it silently never applied to any run, including jest ones.
`_detect_js_runner` now reads jest-vs-vitest from the same package.json
script `testquality.py` already verified passes (via the shared
`core.lang.pick_unit_script` / `detect_js_test_runner`), so the two modules
can't disagree; the env-var gate now defaults to the real `TEST_TYPE` name
and only applies to jest, since vitest has no documented equivalent need.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.lang import (
    MUTATION_SUPPORTED,
    TEST_FILE_RE,
    detect_js_test_runner,
    detect_repo_language,
    pick_unit_script,
)
from ..core.util import run, write_csv, write_json


@dataclass
class MutationResult:
    repo: str
    file_mutated: str
    total_mutants: int
    killed: int
    survived: int
    no_coverage: int
    timeout: int
    mutation_score: float
    ran: bool
    skip_reason: str = ""
    suspicious: int = 0
    segfault: int = 0


def _node20_bin() -> str | None:
    if os.environ.get("REPO_ANALYSER_NODE_BIN"):
        return os.environ["REPO_ANALYSER_NODE_BIN"]
    nvm_versions = Path.home() / ".nvm" / "versions" / "node"
    if nvm_versions.is_dir():
        candidates = sorted(nvm_versions.glob("v20.*"), reverse=True)
        if candidates:
            return str(candidates[0] / "bin")
    return None


NODE20_BIN = _node20_bin()


# Stryker dispatches to a separate plugin package per test runner -- unlike
# jest/vitest detection itself, this isn't guessable from one shared
# constant, so it's kept as its own explicit map rather than folded into
# core/lang.py (which only knows "jest" vs "vitest" as strings, not which
# npm package implements each in Stryker).
STRYKER_RUNNER_PACKAGE = {
    "jest": "@stryker-mutator/jest-runner",
    "vitest": "@stryker-mutator/vitest-runner",
}


def _install_stryker(repo: Path, runner: str) -> bool:
    binary = repo / "node_modules" / ".bin" / "stryker"
    if binary.exists():
        return True
    # --ignore-scripts: this installs tool-chosen, trusted packages
    # (Stryker + its runner plugin), but *inside* whatever arbitrary
    # (possibly compromised) target repo this tool is pointed at -- a
    # malicious repo's own .npmrc/registry config could otherwise try to
    # hijack the install via a postinstall script. See docs/ARCHITECTURE.md
    # "Security model". Neither package needs install-time scripts to work
    # as a CLI invoked directly via its node_modules/.bin path.
    res = run(["npm", "install", "--no-audit", "--no-fund", "--no-save", "--legacy-peer-deps",
               "--ignore-scripts", "@stryker-mutator/core", STRYKER_RUNNER_PACKAGE[runner]],
              cwd=repo, check=False, timeout=180, extra_path=NODE20_BIN)
    return res.returncode == 0 and binary.exists()


def _detect_js_runner(repo: Path) -> str:
    """jest vs vitest, via the same package.json script testquality.py uses
    to verify the suite passes -- so mutation testing never targets a
    different runner than the one that was actually verified green. Real
    bug found by the hardcoding audit: this used to be hardcoded to "jest"
    unconditionally, which made mutation testing silently produce
    "no tests found" for every vitest repo in a portfolio (see
    docs/METHODOLOGY.md)."""
    pkg_path = repo / "package.json"
    if not pkg_path.exists():
        return "unknown"
    scripts = json.loads(pkg_path.read_text()).get("scripts", {})
    script = pick_unit_script(scripts)
    if not script:
        return "unknown"
    return detect_js_test_runner(scripts[script])


def _analyze_js_repo(repo: Path, target_file: str, jest_config: str = "jest.config.js",
                      test_type_env: str = "TEST_TYPE",
                      tmp_dir: Path = Path("/tmp/repo_analyser_mutation")) -> MutationResult:
    if not (repo / target_file).exists():
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"target file not found: {target_file}")
    runner = _detect_js_runner(repo)
    if runner == "unknown":
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason="could not detect jest vs vitest from package.json scripts")
    if not _install_stryker(repo, runner):
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason="stryker install failed (see npm log)")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_dir / f"{repo.name}.stryker.json"
    report_dir = tmp_dir / f"{repo.name}-report"
    # jest needs its config file (and projectType) spelled out explicitly --
    # verified by dogfooding, see module docstring point 3. vitest's own
    # runner auto-discovers vitest.config.{js,ts} (or a `test` block in
    # vite.config.ts) on its own, so no config filename is guessed here --
    # hardcoding one would just reintroduce this same bug for vitest repos
    # that name theirs differently. `related: False` is also required --
    # verified by a real end-to-end run against a real vitest fixture
    # (docs/METHODOLOGY.md #26): Stryker's vitest-runner defaults
    # `related: true` (only run tests it thinks are related to the mutated
    # file), and its own detection failed even against a trivial fixture
    # whose one test file directly imports the one source file -- a real,
    # Stryker-documented unreliability
    # (stryker-mutator.io/docs/stryker-js/troubleshooting/#vitest-failed-to-find-test-files-related-to-mutated-files),
    # not something specific to this tool's repos. Since this tool mutates
    # arbitrary target repos it doesn't control the test-authoring style
    # of, a silent "no tests found" (which reports as a skip, not an error)
    # is worse than the slower but correct full-suite run `related: False`
    # forces.
    runner_config = ({"projectType": "custom", "configFile": jest_config, "enableFindRelatedTests": False}
                      if runner == "jest" else {"related": False})
    config = {
        "packageManager": "npm", "testRunner": runner,
        "mutate": [target_file], "reporters": ["json"],
        "concurrency": 2, "timeoutMS": 30000,
        "tempDirName": str(tmp_dir / f"{repo.name}-tmp"),
        "htmlReporter": {"fileName": str(report_dir / "report.html")},
    }
    if runner_config:
        config[runner] = runner_config
    config_path.write_text(json.dumps(config))

    # The TEST_TYPE-gated testMatch trick (see module docstring point 3) is
    # a real, verified quirk of this portfolio's *jest* configs specifically
    # -- vitest has no documented equivalent need, so it's not applied there
    # (forcing an unasked-for env var into a vitest run would just be a new
    # unverified guess in place of the old one).
    env_extra = {test_type_env: "unit"} if (runner == "jest" and test_type_env) else {}
    binary = repo / "node_modules" / ".bin" / "stryker"
    proc_env = dict(os.environ)
    if NODE20_BIN:
        proc_env["PATH"] = f"{NODE20_BIN}:{proc_env.get('PATH', '')}"
    proc_env.update(env_extra)
    res = subprocess.run([str(binary), "run", str(config_path)], cwd=repo, capture_output=True,
                          text=True, timeout=180, env=proc_env)
    combined = res.stdout + res.stderr
    if "No tests were executed" in combined:
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"{runner} found no tests -- check test_type_env/jest_config")

    mutation_json = repo / "reports" / "mutation" / "mutation.json"
    if not mutation_json.exists():
        # head, not tail: this branch's most commonly observed real
        # failure (3 of 4 mutation-eligible repos in a real portfolio run
        # -- docs/METHODOLOGY.md #31) is a Node.js uncaught-exception dump,
        # which prints the actual error type/message FIRST, then stack
        # frames, then the engine version last. A tail slice here used to
        # capture only "...at Command.<anonymous> (...) { innerError:
        # undefined }\n\nNode.js vX.Y.Z" -- confirmed from the real
        # captured (truncated) text in analyses/posx_after/FINDINGS.md
        # §11 -- losing the one line that would have named the real
        # cause. Head, and generous enough to actually include it.
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"no mutation.json produced -- see raw output: {combined[:2000]}")
    data = json.loads(mutation_json.read_text())
    statuses = [m["status"] for f in data.get("files", {}).values() for m in f.get("mutants", [])]
    killed = statuses.count("Killed")
    survived = statuses.count("Survived")
    no_cov = statuses.count("NoCoverage")
    timeout_n = statuses.count("Timeout")
    total = len(statuses)
    covered = killed + survived + timeout_n
    score = round(100 * killed / covered, 1) if covered else 0.0
    return MutationResult(repo.name, target_file, total, killed, survived, no_cov, timeout_n, score, True)


# mutmut 3.3.1's `mutmut results` output: one "<qualified_name>: <status>"
# line per mutant, e.g. "calc.x_add__mutmut_1: killed". Grounded against
# mutmut/__main__.py's status_by_exit_code (not guessed): the vocabulary is
# killed, survived, timeout, suspicious, skipped, "no tests", segfault.
MUTMUT_RESULT_LINE_RE = re.compile(r"^\s*(?P<name>\S+):\s*(?P<status>.+?)\s*$", re.MULTILINE)


def _parse_mutmut_results(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in MUTMUT_RESULT_LINE_RE.finditer(text):
        status = m.group("status").strip().lower().replace(" ", "_")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _mutmut_setup_cfg_text(target_file: str, tests_dir: str) -> str:
    # mutmut 3.3.1 prints a deprecation warning suggesting `source_paths`
    # in place of `paths_to_mutate`, but verified by actually running it:
    # `source_paths=` in a setup.cfg [mutmut] section is NOT accepted --
    # mutmut errors with "please specify it by adding paths_to_mutate=...".
    # Caught immediately because this exact rename was tried and it broke
    # every real-execution test in this suite; kept on `paths_to_mutate`
    # deliberately (a working deprecated key beats a broken suggested one)
    # until mutmut's actual accepted replacement is confirmed. Same
    # reasoning applies to `tests_dir`, left as-is.
    #
    # use_setproctitle=False is forced explicitly rather than left to
    # mutmut's own Darwin default -- see module docstring point 4 and
    # docs/METHODOLOGY.md #23: this is not a style choice, it's what stops
    # a fork-unsafe CoreFoundation call from being able to crash the host.
    return (f"[mutmut]\npaths_to_mutate={target_file}\ntests_dir={tests_dir}\n"
            f"use_setproctitle=False\n")


def _detect_tests_dir(repo: Path) -> str:
    for candidate in ("tests", "test"):
        if (repo / candidate).is_dir():
            return candidate
    return "."


def _analyze_python_repo(repo: Path, target_file: str,
                          tmp_dir: Path = Path("/tmp/repo_analyser_mutation")) -> MutationResult:
    if not (repo / target_file).exists():
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"target file not found: {target_file}")
    if not shutil.which("mutmut"):
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason="mutmut not on PATH")

    setup_cfg = repo / "setup.cfg"
    # Never leave the target repo's tree changed: back up any existing
    # setup.cfg and restore it verbatim afterward, rather than assuming the
    # repo has none of its own (a real repo may use setup.cfg for flake8,
    # coverage, etc. -- clobbering it, even temporarily and even if we
    # "restore" it, would be a real risk if we ever failed to reach the
    # restore step, so the restore is in a finally block).
    original_contents = setup_cfg.read_text() if setup_cfg.exists() else None
    mutants_dir = repo / "mutants"
    try:
        setup_cfg.write_text(_mutmut_setup_cfg_text(target_file, _detect_tests_dir(repo)))
        run(["mutmut", "run"], cwd=repo, check=False, timeout=180)
        # --all true: mutmut >=3.7 prints nothing on a plain `results` call
        # (see module docstring point 2) -- without this the parser always
        # sees empty output and every run is reported as failed.
        results = run(["mutmut", "results", "--all", "true"], cwd=repo, check=False, timeout=60)
    finally:
        if original_contents is not None:
            setup_cfg.write_text(original_contents)
        else:
            setup_cfg.unlink(missing_ok=True)
        if mutants_dir.is_dir():
            shutil.rmtree(mutants_dir, ignore_errors=True)

    counts = _parse_mutmut_results(results.stdout)
    if not counts:
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"mutmut produced no parseable results -- see raw output: "
                                           f"{(results.stdout + results.stderr)[-500:]}")

    killed = counts.get("killed", 0)
    survived = counts.get("survived", 0)
    # mutmut reports "no tests" per-mutant (a specific function has no
    # covering test) but "not_checked" for a whole run it aborts early
    # when NO mutant in the file has any covering test at all ("Stopping
    # early, because we could not find any test case for any mutant" --
    # observed directly by dogfooding this on this tool's own charts.py,
    # which has zero test coverage). Both mean the same thing to a report
    # reader -- no coverage exists to check -- so both fold into no_cov.
    no_cov = counts.get("no_tests", 0) + counts.get("not_checked", 0)
    timeout_n = counts.get("timeout", 0)
    suspicious = counts.get("suspicious", 0)
    segfault = counts.get("segfault", 0)
    total = sum(counts.values())
    # "suspicious" (result varied across repeated runs) and "segfault"
    # (the runner subprocess itself crashed -- see module docstring) are
    # neither a clean kill nor a clean survive; excluded from the
    # denominator rather than guessed into either bucket.
    covered = killed + survived + timeout_n
    score = round(100 * killed / covered, 1) if covered else 0.0
    return MutationResult(repo.name, target_file, total, killed, survived, no_cov, timeout_n, score, True,
                           suspicious=suspicious, segfault=segfault)


def analyze_repo(repo: Path, target_file: str, jest_config: str = "jest.config.js",
                  test_type_env: str = "TEST_TYPE",
                  tmp_dir: Path = Path("/tmp/repo_analyser_mutation")) -> MutationResult:
    lang = detect_repo_language(repo)
    if lang == "python":
        return _analyze_python_repo(repo, target_file, tmp_dir)
    if lang not in MUTATION_SUPPORTED:
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"language '{lang}' not supported by mutation testing "
                                           f"(supported: {sorted(MUTATION_SUPPORTED)})")
    return _analyze_js_repo(repo, target_file, jest_config, test_type_env, tmp_dir)


def select_mutation_targets(out_dir: Path, repos: list[Path]) -> list[tuple[Path, str]]:
    """Only repos with a fully-passing unit suite (testquality.py's output)
    are eligible -- a failing suite has no meaningful mutation-score
    baseline. Of those, only the single highest hotspot_score file that is
    NOT itself a test file (complexity.py's output: total_ccn x n_revs) is
    mutated, to keep runtime bounded. Test files are excluded even if they
    top the raw hotspot ranking -- mutating a test file answers nothing,
    since there's no separate source left for its own now-mutated
    assertions to have an opinion about (found by dogfooding: an early run
    on this tool's own test-heavy portfolio picked
    tests/collectors/test_churn.py and produced a meaningless all-
    "skipped" result). Raises if the prerequisite CSVs don't exist at all
    (run testquality and complexity first) -- an empty *list* is a real,
    valid answer (no repo currently qualifies); a missing *CSV* is a
    precondition violation, and conflating the two would hide the second
    behind output that silently looks like the first (ADR-0001)."""
    testquality_csv = out_dir / "testquality_runs.csv"
    hotspots_csv = out_dir / "complexity_hotspots.csv"
    if not testquality_csv.exists() or not hotspots_csv.exists():
        missing = ", ".join(p.name for p in (testquality_csv, hotspots_csv) if not p.exists())
        raise FileNotFoundError(f"run the testquality and complexity modules before mutation (missing: {missing})")

    with open(testquality_csv) as f:
        passing_repos = {
            row["repo"] for row in csv.DictReader(f)
            if row.get("ran") == "True" and row.get("exit_code") == "0" and int(row.get("tests_total", 0) or 0) > 0
        }
    top_hotspot_by_repo: dict[str, tuple[str, float]] = {}
    with open(hotspots_csv) as f:
        for row in csv.DictReader(f):
            repo = row["repo"]
            if TEST_FILE_RE.search(row["file"]):
                continue
            score = float(row.get("hotspot_score", 0) or 0)
            if repo not in top_hotspot_by_repo or score > top_hotspot_by_repo[repo][1]:
                top_hotspot_by_repo[repo] = (row["file"], score)

    targets = []
    for repo_path in repos:
        if repo_path.name in passing_repos and repo_path.name in top_hotspot_by_repo:
            targets.append((repo_path, top_hotspot_by_repo[repo_path.name][0]))
    return targets


def run_mutation(targets: list[tuple[Path, str]], out_dir: Path, tmp_dir: Path) -> Path:
    """targets: list of (repo_path, relative_file_to_mutate) -- see
    select_mutation_targets() for the eligibility rule this tool applies.

    Deliberately sequential -- do NOT wrap this in core.util.run_concurrent
    or any other parallelism. mutmut and Stryker each already fork their
    own worker subprocesses internally; stacking this tool's own
    concurrency on top would multiply the exact macOS fork-crash hazard
    that caused a real kernel panic during this tool's own development
    (docs/METHODOLOGY.md #23), not just add load."""
    rows = [asdict(analyze_repo(repo, f, tmp_dir=tmp_dir)) for repo, f in targets]
    out_path = out_dir / "mutation_results.csv"
    write_csv(out_path, rows, fieldnames=MutationResult)
    ran = [r for r in rows if r["ran"]]
    write_json(out_dir / "mutation_summary.json", {
        "repos_attempted": len(rows), "repos_succeeded": len(ran),
        "mean_mutation_score": round(sum(r["mutation_score"] for r in ran) / len(ran), 1) if ran else None,
        "skip_reasons": {r["repo"]: r["skip_reason"] for r in rows if not r["ran"]},
    })
    return out_path
