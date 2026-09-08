"""Signal 3: spec-to-implementation contract-test tooling -- dependency-
manifest entries, known config files/dirs, or a CI step invoking Dredd,
Prism, Schemathesis, or Pact. Three independent detection routes per tool;
any one is sufficient, matching this collector's general "presence of
practice," not "ran the tool" scope (see package docstring)."""
from __future__ import annotations

import json
from pathlib import Path

from .ci_workflows import load_workflow_docs, step_texts
from .patterns import CONTRACT_TEST_CI_PATTERNS, CONTRACT_TEST_CONFIG_PATHS, CONTRACT_TEST_DEPENDENCY_NAMES


def _package_json_deps(repo: Path) -> set[str]:
    p = repo / "package.json"
    if not p.is_file():
        return set()
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(doc, dict):
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        section = doc.get(key)
        if isinstance(section, dict):
            names.update(section.keys())
    return names


def _requirements_names(repo: Path) -> set[str]:
    names: set[str] = set()
    for fname in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        p = repo / fname
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        names.update(word for word in ("schemathesis", "pact-python", "pact_python") if word in text)
    return names


def _dependency_hit(repo: Path, tool: str) -> bool:
    all_names = _package_json_deps(repo) | _requirements_names(repo)
    return any(dep in all_names for dep in CONTRACT_TEST_DEPENDENCY_NAMES[tool])


def _config_hit(repo: Path, tool: str) -> bool:
    for rel in CONTRACT_TEST_CONFIG_PATHS.get(tool, []):
        p = repo / rel
        if p.is_file() or p.is_dir():
            return True
    return False


def contract_test_tools_detected(repo: Path) -> set[str]:
    docs, _errors = load_workflow_docs(repo)
    all_ci_text = " ".join(text for doc in docs for text in step_texts(doc))
    found: set[str] = set()
    for tool in CONTRACT_TEST_DEPENDENCY_NAMES:
        if (
            _dependency_hit(repo, tool)
            or _config_hit(repo, tool)
            or CONTRACT_TEST_CI_PATTERNS[tool].search(all_ci_text)
        ):
            found.add(tool)
    return found
