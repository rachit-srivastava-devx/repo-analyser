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
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

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


@dataclass
class E2EResult:
    repo: str
    has_e2e_suite: bool
    frameworks_detected: str
    detected_via: str
    wired_into_ci: bool


def _detect_frameworks_from_package_json(repo: Path) -> set[str]:
    pj = repo / "package.json"
    if not pj.exists():
        return set()
    try:
        data = json.loads(pj.read_text())
    except json.JSONDecodeError:
        return set()
    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    return {E2E_PACKAGE_SIGNALS[name] for name in all_deps if name in E2E_PACKAGE_SIGNALS}


def _detect_frameworks_from_config_files(repo: Path) -> set[str]:
    return {framework for framework, filenames in E2E_CONFIG_FILES.items()
            if any((repo / name).exists() for name in filenames)}


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


def _frameworks_wired_into_ci(repo: Path, frameworks: set[str]) -> bool:
    docs = _load_workflow_docs(repo)
    all_text = " ".join(text for doc in docs for text in _step_texts(doc))
    return any(E2E_CI_COMMAND_PATTERNS[fw].search(all_text) for fw in frameworks if fw in E2E_CI_COMMAND_PATTERNS)


def analyze_repo(repo: Path) -> E2EResult:
    from_pkg = _detect_frameworks_from_package_json(repo)
    from_config = _detect_frameworks_from_config_files(repo)
    frameworks = from_pkg | from_config
    if not frameworks:
        return E2EResult(repo.name, False, "", "", False)
    detected_via = "both" if (from_pkg and from_config) else ("package.json" if from_pkg else "config_file")
    return E2EResult(
        repo=repo.name, has_e2e_suite=True, frameworks_detected=";".join(sorted(frameworks)),
        detected_via=detected_via, wired_into_ci=_frameworks_wired_into_ci(repo, frameworks),
    )


def run_e2e_quality(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "e2e_quality.csv"
    write_csv(out_path, rows)
    with_suite = [r for r in rows if r["has_e2e_suite"]]
    write_json(out_dir / "e2e_quality_summary.json", {
        "repos_total": len(rows),
        "repos_with_e2e_suite": len(with_suite),
        "repos_with_e2e_wired_into_ci": sum(1 for r in with_suite if r["wired_into_ci"]),
    })
    return out_path
