"""Orphaned-Django-migration detection: a migration's own `dependencies =
[...]` names a sibling migration (by app label + name) that this collector
never found in the same discovered set for that app.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .text_io import read_text_safe


def find_django_orphans(paths: list[Path]) -> list[str]:
    """A Django migration whose `dependencies` list names a sibling
    migration, *within the same app* (`app/migrations/000x_*.py` -- app
    label is the migrations dir's parent), that isn't among the migration
    files this collector found for that app. A cross-app dependency
    (a different app_label) is deliberately not checked -- this collector
    only discovers one repo's files, and resolving another app's true
    label would need Django's own app registry, not a static file read;
    skipped rather than misreported as an orphan.

    Best-effort: only recognizes a literal `dependencies = [("app",
    "name"), ...]` list -- a dynamically-built dependencies list can't be
    resolved by a static AST read, and is silently skipped."""
    by_app: dict[str, set[str]] = {}
    for p in paths:
        by_app.setdefault(p.parent.parent.name, set()).add(p.stem)

    orphans: list[str] = []
    for p in paths:
        app_label = p.parent.parent.name
        text, err = read_text_safe(p)
        if err or text is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.List)):
                continue
            if not any(isinstance(t, ast.Name) and t.id == "dependencies" for t in node.targets):
                continue
            for elt in node.value.elts:
                if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2):
                    continue
                dep_app, dep_name = elt.elts
                if not (isinstance(dep_app, ast.Constant) and isinstance(dep_app.value, str)
                        and isinstance(dep_name, ast.Constant) and isinstance(dep_name.value, str)):
                    continue
                dep_name_value: str = dep_name.value
                if dep_app.value != app_label:
                    continue  # cross-app -- can't resolve, deliberately skipped
                if dep_name_value not in by_app.get(app_label, set()):
                    orphans.append(f"{p.name}->{dep_name_value}")
    return orphans
