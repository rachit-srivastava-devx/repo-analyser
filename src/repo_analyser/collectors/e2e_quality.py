"""E2E test-suite detection: does this repo have an end-to-end test suite
(Playwright/Cypress/Selenium-style), and is it actually wired into CI --
a real, previously-uncovered gap, not a rehash of testquality.py (which
is deliberately scoped to unit tests only, see its own docstring).

ci_gates.py's own "does any workflow run tests" check already matches
`playwright test`/`cypress run` as a side effect of its generic TEST_RE,
but that conflates E2E and unit-test commands into one boolean rather
than answering "does an E2E suite exist, and does CI actually run it" as
its own question -- which is what this module answers, with its own
narrower, framework-specific command patterns.

Two independent detection signals, checked separately rather than either
alone, since a repo can have the npm package listed as a devDependency
some contributors haven't installed a config for yet, or a config file
committed without (or before) the package being formally declared:
  1. package.json dependency/devDependency names
  2. a framework's own conventional config file at the repo root

Scope, stated honestly rather than silently assumed: JS/TS only.
Playwright-Python, Python Selenium bindings, etc. are real and not
covered here -- would need a different detection signal
(requirements.txt/pyproject.toml package names) not yet built.

2026-09-06 extension (docs/ROADMAP.md "e2e_quality.py" bullet): six more
narrowly-scoped signals, additive to the original two above and to each
other -- visual-regression config, flake-retry config, sharding config,
a11y-in-e2e, trace/video-on-failure config, and network-mock contract
fidelity. Same "presence/config-grep, no new subprocess tool" shape as
everything above; none of these judge a config *value*, only whether the
relevant key/dependency/API call is present at all. The a11y signal is
the one exception to the JS/TS-only scope stated above: it also checks
requirements.txt for axe-playwright-python, since skipping the Python
half of a mixed portfolio would silently undercount a real, common case.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from ..core.lang import EXCLUDE_DIR_PARTS, TEST_FILE_RE
from ..core.util import write_csv, write_json

# CI-step text patterns for each framework's own actual test-run command --
# deliberately narrower than ci_gates.py's own generic TEST_RE (which only
# answers "did *some* test command run," not "was it specifically this
# repo's E2E suite"). Kept local rather than imported from ci_gates.py:
# this codebase's own convention (docs/ARCHITECTURE.md) treats a sibling
# collector-to-collector import as a rare, explicitly-noted exception
# (escape.py importing ontology.classify_commit is the one), not a default.
E2E_CI_COMMAND_PATTERNS = {
    "playwright": re.compile(r"\bplaywright\s+test\b", re.IGNORECASE),
    "cypress": re.compile(r"\bcypress\s+(run|open)\b", re.IGNORECASE),
    "selenium/webdriver": re.compile(r"\bwdio\s+run\b", re.IGNORECASE),
}

# npm package name -> framework label. Selenium's own package is named
# "selenium-webdriver"; WebdriverIO ("webdriverio"/"@wdio/cli") wraps the
# W3C WebDriver protocol directly and is the realistic way most JS/TS
# repos actually use Selenium today, so both fold into one
# "selenium/webdriver" family rather than two thinly-populated categories.
E2E_PACKAGE_SIGNALS = {
    "@playwright/test": "playwright",
    "playwright": "playwright",
    "cypress": "cypress",
    "selenium-webdriver": "selenium/webdriver",
    "webdriverio": "selenium/webdriver",
    "@wdio/cli": "selenium/webdriver",
}

# A framework's own conventional config filename(s) at the repo root.
E2E_CONFIG_FILES = {
    "playwright": ["playwright.config.ts", "playwright.config.js", "playwright.config.mjs"],
    "cypress": ["cypress.config.ts", "cypress.config.js", "cypress.json"],
    "selenium/webdriver": ["wdio.conf.ts", "wdio.conf.js"],
}

# --- 2026-09-06 extension: six more signals, see module docstring. ---

# npm package name -> visual-regression tool label. `toHaveScreenshot` is
# Playwright's own built-in snapshot assertion (no package to depend on --
# it ships with @playwright/test itself), so it's detected by grepping
# test source instead of this table; see _test_source_contains below.
VISUAL_REGRESSION_PACKAGE_SIGNALS = {"@percy/playwright": "percy", "chromatic": "chromatic"}

# npm package name -> a11y-in-e2e tool label (JS/TS half of that signal).
A11Y_JS_PACKAGE_SIGNALS = {"@axe-core/playwright": "axe-core-playwright"}
# PyPI package name for the Python half -- checked separately via
# requirements.txt, see _python_requirements_deps below.
A11Y_PYTHON_PACKAGE = "axe-playwright-python"

PACT_PACKAGE_NAME = "@pact-foundation/pact"

# Key-presence patterns against a config file's own raw text -- never a
# real TS/JS parse (playwright.config.ts is arbitrary TypeScript, not
# data), and never a judgment on the key's *value*, matching this
# module's existing "presence, not full execution" shape. The optional
# quote before the colon matters: cypress.json (still in E2E_CONFIG_FILES
# as a legacy format) writes keys as `"retries": 2`, not `retries: 2` --
# without it, this would silently never match that file.
RETRIES_KEY_RE = re.compile(r"\bretries\b\s*[\"']?\s*:")
SHARD_KEY_RE = re.compile(r"\bshard\b\s*[\"']?\s*:")
CI_SHARD_FLAG_RE = re.compile(r"--shard\b")
TRACE_OR_VIDEO_KEY_RE = re.compile(r"\b(trace|video)\b\s*[\"']?\s*:")

# Bare package-name extraction from one requirements.txt line, e.g.
# "axe-playwright-python==1.2.0" -> "axe-playwright-python". Mirrors
# graph/knowledge_graph.py's own _python_deps (requirements.txt only --
# pyproject.toml's [project.dependencies]/[tool.poetry.dependencies]
# would need a TOML parser, same documented gap, not silently missed).
# Duplicated locally rather than imported: graph/ reads collectors'
# *output files*, never their code (docs/ARCHITECTURE.md), so a collector
# importing back from graph/ would invert that dependency direction.
_REQUIREMENT_SPECIFIER_RE = re.compile(r"[=<>!~\[; ]")


@dataclass
class E2EResult:
    repo: str
    has_e2e_suite: bool
    frameworks_detected: str
    detected_via: str
    wired_into_ci: bool
    # --- 2026-09-06 extension: appended, existing columns untouched. ---
    has_visual_regression: bool
    visual_regression_signals: str
    has_flake_retry_config: bool
    has_sharding_config: bool
    has_a11y_in_e2e: bool
    a11y_tools: str
    has_trace_or_video_config: bool
    has_network_mock_contract_fidelity: bool


def _read_package_json_deps(repo: Path) -> dict:
    # Shared by every package.json-based signal in this module (E2E
    # frameworks, visual-regression, a11y, network-mock) so package.json
    # is read and parsed once per repo, not once per signal.
    pj = repo / "package.json"
    if not pj.exists():
        return {}
    try:
        data = json.loads(pj.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return {**data.get("dependencies", {}), **data.get("devDependencies", {})}


def _detect_frameworks_from_package_json(repo: Path) -> set[str]:
    all_deps = _read_package_json_deps(repo)
    return {E2E_PACKAGE_SIGNALS[name] for name in all_deps if name in E2E_PACKAGE_SIGNALS}


def _detect_frameworks_from_config_files(repo: Path) -> set[str]:
    return {framework for framework, filenames in E2E_CONFIG_FILES.items()
            if any((repo / name).exists() for name in filenames)}


def _test_source_files(repo: Path) -> list[Path]:
    # Same walk shape as core.lang.detect_repo_language: exclude
    # EXCLUDE_DIR_PARTS, only files (not dirs). Narrowed to JS/TS test
    # files specifically -- toHaveScreenshot is a Playwright/JS API, and
    # this module's non-a11y signals are JS/TS-only by design (docstring).
    js_ts_exts = {".ts", ".tsx", ".js", ".jsx"}
    out = []
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.suffix not in js_ts_exts:
            continue
        if TEST_FILE_RE.search(p.relative_to(repo).as_posix()):
            out.append(p)
    return out


def _test_source_contains(repo: Path, needle: str) -> bool:
    return any(needle in p.read_text(errors="ignore") for p in _test_source_files(repo))


def _detect_visual_regression_signals(repo: Path, pkg_deps: dict) -> set[str]:
    signals = {VISUAL_REGRESSION_PACKAGE_SIGNALS[name] for name in pkg_deps
               if name in VISUAL_REGRESSION_PACKAGE_SIGNALS}
    if _test_source_contains(repo, "toHaveScreenshot"):
        signals.add("playwright-snapshots")
    return signals


def _python_requirements_deps(repo: Path) -> set[str]:
    req = repo / "requirements.txt"
    if not req.exists():
        return set()
    deps = set()
    for line in req.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = _REQUIREMENT_SPECIFIER_RE.split(line, 1)[0].strip()
        if name:
            deps.add(name.lower())
    return deps


def _detect_a11y_tools(repo: Path, pkg_deps: dict) -> set[str]:
    tools = {A11Y_JS_PACKAGE_SIGNALS[name] for name in pkg_deps if name in A11Y_JS_PACKAGE_SIGNALS}
    if A11Y_PYTHON_PACKAGE in _python_requirements_deps(repo):
        tools.add("axe-playwright-python")
    return tools


def _load_workflow_docs(repo: Path) -> list[dict]:
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return []
    docs = []
    for f in sorted(p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")):
        try:
            doc = yaml.safe_load(f.read_text())
        except yaml.YAMLError:
            # ci_gates.py already reports an unparseable workflow loudly
            # (ADR-0001) as part of *its* metric; this module's own
            # question is narrower ("is an E2E command present"), so a
            # workflow it can't parse is treated the same as one with no
            # matching command, not re-raised here.
            continue
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def _step_texts(doc: dict) -> list[str]:
    texts = []
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if isinstance(step, dict):
                texts.append(f"{step.get('run', '')} {step.get('uses', '')}")
    return texts


def _all_ci_step_text(repo: Path) -> str:
    docs = _load_workflow_docs(repo)
    return " ".join(text for doc in docs for text in _step_texts(doc))


def _frameworks_wired_into_ci(repo: Path, frameworks: set[str]) -> bool:
    all_text = _all_ci_step_text(repo)
    return any(E2E_CI_COMMAND_PATTERNS[fw].search(all_text) for fw in frameworks if fw in E2E_CI_COMMAND_PATTERNS)


def _existing_config_paths(repo: Path, frameworks: list[str]) -> list[Path]:
    return [repo / name for framework in frameworks
            for name in E2E_CONFIG_FILES.get(framework, []) if (repo / name).exists()]


def _config_text_matches(repo: Path, frameworks: list[str], pattern: re.Pattern[str]) -> bool:
    return any(pattern.search(p.read_text(errors="ignore")) for p in _existing_config_paths(repo, frameworks))


def analyze_repo(repo: Path) -> E2EResult:
    pkg_deps = _read_package_json_deps(repo)
    from_pkg = {E2E_PACKAGE_SIGNALS[name] for name in pkg_deps if name in E2E_PACKAGE_SIGNALS}
    from_config = _detect_frameworks_from_config_files(repo)
    frameworks = from_pkg | from_config
    detected_via = ("both" if (from_pkg and from_config)
                     else "package.json" if from_pkg
                     else "config_file" if from_config
                     else "")
    # Skip CI-workflow parsing entirely when there's no framework to match
    # against -- matches the original early-return's intent (never do the
    # YAML-parsing work when it provably can't change the answer).
    wired_into_ci = _frameworks_wired_into_ci(repo, frameworks) if frameworks else False

    # Every signal below is independent of has_e2e_suite: a repo can carry
    # an a11y/visual-regression/pact dependency, or a CI --shard flag,
    # without this module having matched a full E2E framework -- see
    # module docstring's 2026-09-06 extension note.
    visual_regression_signals = _detect_visual_regression_signals(repo, pkg_deps)
    a11y_tools = _detect_a11y_tools(repo, pkg_deps)

    return E2EResult(
        repo=repo.name, has_e2e_suite=bool(frameworks), frameworks_detected=";".join(sorted(frameworks)),
        detected_via=detected_via, wired_into_ci=wired_into_ci,
        has_visual_regression=bool(visual_regression_signals),
        visual_regression_signals=";".join(sorted(visual_regression_signals)),
        has_flake_retry_config=_config_text_matches(repo, ["playwright", "cypress"], RETRIES_KEY_RE),
        has_sharding_config=(_config_text_matches(repo, ["playwright"], SHARD_KEY_RE)
                             or bool(CI_SHARD_FLAG_RE.search(_all_ci_step_text(repo)))),
        has_a11y_in_e2e=bool(a11y_tools), a11y_tools=";".join(sorted(a11y_tools)),
        has_trace_or_video_config=_config_text_matches(repo, ["playwright"], TRACE_OR_VIDEO_KEY_RE),
        has_network_mock_contract_fidelity=PACT_PACKAGE_NAME in pkg_deps,
    )


def run_e2e_quality(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "e2e_quality.csv"
    write_csv(out_path, rows, fieldnames=E2EResult)
    with_suite = [r for r in rows if r["has_e2e_suite"]]
    write_json(out_dir / "e2e_quality_summary.json", {
        "repos_total": len(rows),
        "repos_with_e2e_suite": len(with_suite),
        "repos_with_e2e_wired_into_ci": sum(1 for r in with_suite if r["wired_into_ci"]),
    })
    return out_path
