"""Shared fixture-building helpers for the api_contract test package.
Named per-collector (not the generic `_helpers.py`) because tests/ has no
`__init__.py` anywhere -- pytest's prepend import mode means a generic name
would collide with every other collector's identically-named helper module
in sys.modules the moment the full suite runs together (AGENTS.md §4)."""
from __future__ import annotations

from pathlib import Path


def write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def workflow(repo: Path, name: str, content: str) -> Path:
    return write(repo, f".github/workflows/{name}", content)


OPENAPI_MIN = """openapi: 3.0.0
info: {title: t, version: "1.0"}
paths: {}
"""

OPENAPI_WITH_DEPRECATIONS = """openapi: 3.0.0
info: {title: t, version: "1.0"}
paths:
  /users:
    get:
      deprecated: true
      x-sunset: 2026-01-01
      responses: {'200': {description: ok}}
  /legacy:
    get:
      deprecated: true
      responses: {'200': {description: ok}}
"""
