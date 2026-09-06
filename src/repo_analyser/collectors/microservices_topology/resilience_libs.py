"""Signal (e): resilience-library dependency presence, by name, per
language -- JS (opossum, cockatiel in package.json
dependencies/devDependencies), Python (pybreaker, tenacity in
requirements.txt/pyproject.toml), Go (sony/gobreaker, avast/retry-go in
go.mod). PRESENCE ONLY -- whether the declared breaker/retry logic is
actually correct (right timeout, right backoff, wraps the right call)
needs AST-level judgment, explicitly out of v1 scope per
docs/ROADMAP.md."""
from __future__ import annotations

from pathlib import Path

from .fs_helpers import _read_json, _read_text
from .models import _PY_RESILIENCE_PATTERNS, RESILIENCE_LIBS_GO, RESILIENCE_LIBS_JS


def _resilience_libs_detected(repo: Path) -> set[str]:
    found: set[str] = set()

    pkg = _read_json(repo / "package.json")
    all_js_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    found |= {name for name in RESILIENCE_LIBS_JS if name in all_js_deps}

    py_text = _read_text(repo / "requirements.txt") + "\n" + _read_text(repo / "pyproject.toml")
    found |= {name for name, pattern in _PY_RESILIENCE_PATTERNS.items() if pattern.search(py_text)}

    go_text = _read_text(repo / "go.mod")
    found |= {name for name in RESILIENCE_LIBS_GO if name in go_text}

    return found
