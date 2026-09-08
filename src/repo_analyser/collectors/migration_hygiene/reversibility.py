"""Per-file reversibility classification, one function per supported
convention. Every function returns one of "reversible" / "irreversible" /
"unknown" -- "unknown" is reserved for a real parse failure (malformed
file, non-UTF8 content), never used as a synonym for "irreversible" (that
would silently overstate a real finding with a low-confidence one).

Uses `ast.parse` (never `exec`/`eval` -- AGENTS.md §3's "untrusted input"
rung: this reads an arbitrary target repo's own Python source) to inspect
structure without running the migration.

Honesty limitation, stated here rather than only in docs/METHODOLOGY.md:
Django migrations have no separate "down" file at all -- most operations
(AddField, CreateModel, RemoveField, ...) are automatically reversible by
Django's own migration framework, so their *absence* from a migration is
not a red flag. Only `RunPython`/`RunSQL` -- the two escape hatches where
the author supplies arbitrary forward logic -- can be irreversible, and
only when no `reverse_code`/`reverse_sql` companion was given. This
function detects exactly that signal and nothing more; it cannot tell
whether a supplied reverse_code/reverse_sql is *correct*, only whether one
was supplied at all.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .text_io import read_text_safe


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_none_const(node: ast.expr | None) -> bool:
    return node is None or (isinstance(node, ast.Constant) and node.value is None)


def _has_reverse(node: ast.Call, kwarg: str) -> bool:
    for kw in node.keywords:
        if kw.arg == kwarg:
            return not _is_none_const(kw.value)
    if len(node.args) > 1:
        return not _is_none_const(node.args[1])
    return False


def classify_django(path: Path) -> str:
    text, err = read_text_safe(path)
    if err or text is None:
        return "unknown"
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "unknown"

    saw_escape_hatch = False
    saw_unreversed = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name == "RunPython":
            saw_escape_hatch = True
            saw_unreversed |= not _has_reverse(node, "reverse_code")
        elif name == "RunSQL":
            saw_escape_hatch = True
            saw_unreversed |= not _has_reverse(node, "reverse_sql")
    if not saw_escape_hatch:
        return "reversible"  # only auto-reversible schema ops present
    return "irreversible" if saw_unreversed else "reversible"


def classify_sql_pair(down_path: Path | None) -> str:
    if down_path is None:
        return "irreversible"
    text, err = read_text_safe(down_path)
    if err or text is None:
        return "unknown"
    return "irreversible" if text.strip() == "" else "reversible"
