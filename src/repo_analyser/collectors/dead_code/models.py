"""Dataclasses for the dead_code collector's per-repo result and individual
findings. Shapes only, no logic -- see __init__.py for the collector's
overall contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# "cap at ~50" per the brief. A named constant so analyze.py and tests
# agree on the exact number rather than each hardcoding 50 independently.
FINDINGS_CAP = 50


@dataclass
class Finding:
    """One raw dead-code candidate. `kind` is vulture's own finding kind
    ("import" / "function" / "class" / "method" / "attribute" / "variable"
    / "unused-argument" / ...) for python findings, or the literal string
    "unreferenced_export" for js_heuristic findings."""
    language: str  # "python" | "javascript"
    kind: str
    file: str      # repo-relative path
    line: int
    name: str


@dataclass
class DeadCodeResult:
    """One repo's dead-code result.

    `dead_code_items_python` / `unreferenced_export_count_js` are `None`
    when not applicable (no files of that language -- or, python only,
    vulture unavailable) and an `int` -- including a genuine 0 -- once the
    corresponding check actually ran. That distinction is the entire point
    of this shape: a bare 0 must never be ambiguous between "checked,
    found nothing" and "didn't check".

    `findings` is capped at FINDINGS_CAP for detail-output size, but the
    two count fields above are always the *true*, uncapped counts.
    """
    repo: str
    dead_code_items_python: int | None
    unreferenced_export_count_js: int | None
    findings: list[Finding] = field(default_factory=list)
    tool_unavailable: list[str] = field(default_factory=list)
