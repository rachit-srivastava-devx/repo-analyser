"""Signal 2: god class/module detection -- Python only for v1, same
honesty-scoped language-support pattern as depgraph.py's Python/JS/Go
split (core.lang.GOD_CLASS_SUPPORTED). A non-Python-detected repo reports
`god_class_language_supported=False` rather than a bare zero that would
read identically to "genuinely found none in a Python repo" (AGENTS.md §3
rung 9 / §6's "silent empty result" failure mode) -- callers must check
that flag before trusting the count.

Parses every discovered .py file with `ast` (never `exec`/`eval` on a
target repo's own code -- same untrusted-input rung as depgraph.py/
migration_hygiene's reversibility.py), mirroring depgraph.py's exact
error-handling shape: `file.read_text(errors="ignore")` then
`ast.parse(...)`, skipping (not crashing on) a file with a real syntax
error.

**God class**: method count > 20 (direct `FunctionDef`/`AsyncFunctionDef`
children of the class body only -- a nested class's own methods don't
count toward its *containing* class) OR class LOC > 300
(`node.end_lineno - node.lineno + 1`). Both thresholds are strict `>`,
consistent with module_size.py's file/package thresholds. `end_lineno` can
be `None` on some parse paths -- when it is, this class's LOC is treated
as unknown (excluded from the LOC half of the god-class test, not treated
as 0 or as automatically triggering) rather than crashing; the method-
count half still applies since it never depends on end_lineno."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from ...core.lang import GOD_CLASS_SUPPORTED, detect_repo_language
from .discovery import iter_python_files
from .patterns import SAMPLE_CAP, join_sample

GOD_CLASS_METHOD_THRESHOLD = 20
GOD_CLASS_LOC_THRESHOLD = 300


@dataclass
class GodClassFindings:
    god_class_count: int
    god_classes: str
    god_class_language_supported: bool


def _method_count(node: ast.ClassDef) -> int:
    return sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))


def _class_loc(node: ast.ClassDef) -> int | None:
    if node.end_lineno is None:
        return None
    return node.end_lineno - node.lineno + 1


def _find_god_classes_in_file(path: Path, repo: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(errors="ignore"), filename=str(path))
    except SyntaxError:
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = _method_count(node)
        loc = _class_loc(node)
        is_god = methods > GOD_CLASS_METHOD_THRESHOLD or (loc is not None and loc > GOD_CLASS_LOC_THRESHOLD)
        if is_god:
            loc_str = str(loc) if loc is not None else "?"
            hits.append(f"{path.relative_to(repo)}:{node.name}(methods={methods},loc={loc_str})")
    return hits


def find_god_class_findings(repo: Path) -> GodClassFindings:
    language = detect_repo_language(repo)
    if language not in GOD_CLASS_SUPPORTED:
        return GodClassFindings(god_class_count=0, god_classes="", god_class_language_supported=False)

    hits: list[str] = []
    for f in iter_python_files(repo):
        hits += _find_god_classes_in_file(f, repo)

    return GodClassFindings(
        god_class_count=len(hits),
        god_classes=join_sample(sorted(hits), SAMPLE_CAP),
        god_class_language_supported=True,
    )
