"""Alembic reversibility classification -- split out of reversibility.py
to keep both files under the ~80-line convention (AGENTS.md §4).

Signal: whether `downgrade()`'s body is a real implementation or just
`pass`/a bare docstring/`raise NotImplementedError(...)`. Honesty
limitation: a `downgrade()` that runs but doesn't actually undo `upgrade()`
correctly (e.g. drops a column `upgrade()` never added) reads as
"reversible" here -- this is a structural presence check, not a semantic
verification, exactly like the Django module's own stated limitation.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .text_io import read_text_safe


def _is_effectively_empty(body: list[ast.stmt]) -> bool:
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue  # bare docstring
        if isinstance(stmt, ast.Raise):
            continue  # e.g. raise NotImplementedError("irreversible")
        return False
    return True


def classify_alembic(path: Path) -> str:
    text, err = read_text_safe(path)
    if err or text is None:
        return "unknown"
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "unknown"
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            return "irreversible" if _is_effectively_empty(node.body) else "reversible"
    return "unknown"  # no downgrade() found at all -- can't tell from this file alone
