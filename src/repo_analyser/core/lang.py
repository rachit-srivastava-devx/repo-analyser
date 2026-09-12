"""Language detection shared by depgraph.py, testquality.py, and
duplication.py, so "what language is this repo" is answered once, the same
way, everywhere -- rather than each module guessing independently and
possibly disagreeing.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

EXT_TO_LANG = {
    ".ts": "javascript", ".tsx": "javascript", ".js": "javascript",
    ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python",
    ".go": "go",
    ".java": "java", ".kt": "java",
    ".rb": "ruby",
    ".rs": "rust",
}
EXCLUDE_DIR_PARTS = {"node_modules", "dist", "build", ".git", "coverage", ".next", ".turbo",
                     "venv", ".venv", "__pycache__", "vendor", "target"}

# Which languages depgraph.py / testquality.py / mutation.py actually
# implement support for -- kept explicit so an unsupported language reports
# "not supported" rather than silently producing an empty/wrong result.
DEPGRAPH_SUPPORTED = {"javascript", "python", "go"}
TESTQUALITY_SUPPORTED = {"javascript", "python", "go"}
MUTATION_SUPPORTED = {"javascript", "python"}

# codebase_modularity's god-class/god-module signal: Python-only for v1
# (ast.ClassDef method-count/LOC analysis) -- kept explicit here so an
# unsupported-language repo reports "not supported" via
# god_class_language_supported=False rather than a silent zero that reads
# identically to "genuinely found none".
GOD_CLASS_SUPPORTED = {"python"}

# Shared by ontology.py (file-pattern classification) and mutation.py
# (excluding test files from mutation-target eligibility -- mutating a
# test file answers nothing, since there's no separate source left for its
# own now-mutated assertions to have an opinion about; found by dogfooding
# this tool on its own, test-heavy portfolio).
TEST_FILE_RE = re.compile(
    r"(^|/)(__tests__|tests?)/|\.(test|spec)\.[jt]sx?$|(^|/)test_[^/]+\.py$|_test\.py$|_test\.go$"
)

def is_internal_js_module(resolved: str) -> bool:
    # a bare specifier like "@medusajs/framework/workflows-sdk" is an
    # external package reference even when dependency-cruiser doesn't
    # expand it to a literal node_modules/... path (package "exports" map
    # resolution) -- only a relative/rooted path is this repo's own code.
    # Shared by depgraph.py (computing per-repo metrics) and
    # graph.knowledge_graph (reading the same raw dependency-cruiser JSON
    # back off disk for the IMPORTS edge) -- graph/ reads collectors'
    # *output files*, never their code (docs/ARCHITECTURE.md), so this
    # lives in core/ rather than being imported cross-collector.
    return resolved.startswith((".", "/")) and "node_modules" not in resolved


# jscpd's --format language names (https://github.com/kucherenko/jscpd) --
# not always the same string as our internal EXT_TO_LANG values.
JSCPD_FORMAT = {
    "javascript": "javascript,typescript,jsx,tsx",
    "python": "python",
    "go": "go",
    "java": "java",
    "ruby": "ruby",
    "rust": "rust",
}


# JS/TS unit-test script selection, shared by testquality.py (to know which
# package.json script to execute) and mutation.py (to know which script's
# body to inspect for jest-vs-vitest detection) -- both must agree on which
# script a repo uses, or mutation testing could target a different runner
# than the one testquality.py verified actually passes.
UNIT_SCRIPT_PREFERENCE = ["test:unit", "test"]


def pick_unit_script(pkg_scripts: dict) -> str | None:
    for candidate in UNIT_SCRIPT_PREFERENCE:
        if candidate in pkg_scripts:
            return candidate
    return None


def detect_js_test_runner(script_body: str) -> str:
    """vitest vs jest, from a package.json script's own body (e.g. "vitest
    run" vs "jest --coverage") -- checked by substring since real scripts
    wrap the runner with flags/env vars."""
    return "vitest" if "vitest" in script_body else "jest" if "jest" in script_body else "unknown"


def detect_repo_language(repo: Path) -> str:
    """Dominant language by file count. Returns "unknown" if nothing
    recognized is found (e.g. a pure-Terraform or pure-docs repo)."""
    counts: Counter[str] = Counter()
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        lang = EXT_TO_LANG.get(p.suffix)
        if lang:
            counts[lang] += 1
    if not counts:
        return "unknown"
    return counts.most_common(1)[0][0]


def detect_portfolio_languages(repos: list[Path]) -> set[str]:
    return {detect_repo_language(r) for r in repos} - {"unknown"}
