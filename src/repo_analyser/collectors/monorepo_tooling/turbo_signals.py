"""Signal 2: Turborepo (turbo.json). Reports which pipeline-definition
schema was found -- "tasks" (current schema, Turbo >=2.0) or "pipeline"
(legacy schema) -- rather than picking one silently; a repo mid-migration
between the two schemas is a real, reportable state, not an error (same
"report all found" principle the package docstring applies to multiple
orchestrators)."""
from __future__ import annotations

import json
from pathlib import Path

from .config_io import read_text_safe
from .patterns import TURBO_CONFIG_FILENAME


def analyze_turbo(repo: Path) -> tuple[bool, bool, str, int, str | None]:
    """Returns (present, valid_json, schema, task_count, parse_error).
    schema is "tasks", "pipeline", or "" (valid JSON, but neither key holds
    a non-empty object -- a bare scaffold turbo.json)."""
    path = repo / TURBO_CONFIG_FILENAME
    if not path.is_file():
        return False, False, "", 0, None
    text, err = read_text_safe(path)
    if err:
        return True, False, "", 0, err
    assert text is not None
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        return True, False, "", 0, f"{path}: {e}"
    if not isinstance(doc, dict):
        return True, False, "", 0, f"{path}: top level is not a JSON object"
    for schema, key in (("tasks", "tasks"), ("pipeline", "pipeline")):
        value = doc.get(key)
        if isinstance(value, dict) and value:
            return True, True, schema, len(value), None
    return True, True, "", 0, None
