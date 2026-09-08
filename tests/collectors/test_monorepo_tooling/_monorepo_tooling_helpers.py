"""Shared fixture-building helpers for the monorepo_tooling test package.
Named per-collector (not the generic `_helpers.py`) because tests/ has no
`__init__.py` anywhere -- pytest's prepend import mode means a generic name
would collide with every other collector's identically-named helper module
in sys.modules the moment the full suite runs together (AGENTS.md SS4)."""
from __future__ import annotations

from pathlib import Path


def write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


NX_CONFIGURED = """{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "targetDefaults": {
    "build": {"dependsOn": ["^build"]}
  },
  "namedInputs": {
    "default": ["{projectRoot}/**/*"]
  }
}
"""

NX_BARE_SCAFFOLD = """{"$schema": "./node_modules/nx/schemas/nx-schema.json"}
"""

TURBO_TASKS_SCHEMA = """{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {"dependsOn": ["^build"], "outputs": ["dist/**"]},
    "test": {"dependsOn": ["build"]}
  }
}
"""

TURBO_PIPELINE_SCHEMA = """{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {"dependsOn": ["^build"]}
  }
}
"""

PANTS_CONFIGURED = """[GLOBAL]
pants_version = "2.20.0"

[python]
interpreter_constraints = [">=3.10"]
"""
