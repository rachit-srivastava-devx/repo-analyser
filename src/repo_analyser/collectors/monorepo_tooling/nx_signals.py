"""Signal 1: Nx (nx.json). "A real, configured project graph" means at
least one of targetDefaults / tasksRunnerOptions / namedInputs is present
as an object -- a bare `{}` or `{"$schema": "..."}` scaffold default has
none of these and is reported as present-but-unconfigured, not as "no Nx".
project_json_count comes from the shared bounded scan (fs_scan.py), not a
second nx-specific walk -- counting project.json files is a cheap proxy
for workspace-project count, not Nx's own project-graph algorithm (that
needs a live `nx graph` query, explicitly out of scope -- see package
docstring)."""
from __future__ import annotations

import json
from pathlib import Path

from .config_io import read_text_safe
from .patterns import NX_CONFIG_FILENAME, NX_PROJECT_JSON_FILENAME

_CONFIGURED_KEYS = ("targetDefaults", "tasksRunnerOptions", "namedInputs")


def analyze_nx(repo: Path, file_counts: dict[str, int]) -> tuple[bool, bool, bool, int, str | None]:
    """Returns (present, valid_json, has_configured_graph, project_json_count,
    parse_error). present is True the moment nx.json exists, independent of
    whether it parses -- a malformed nx.json is a distinct, reportable
    finding, not "no Nx"."""
    project_count = file_counts.get(NX_PROJECT_JSON_FILENAME, 0)
    path = repo / NX_CONFIG_FILENAME
    if not path.is_file():
        return False, False, False, project_count, None
    text, err = read_text_safe(path)
    if err:
        return True, False, False, project_count, err
    assert text is not None
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        return True, False, False, project_count, f"{path}: {e}"
    if not isinstance(doc, dict):
        return True, False, False, project_count, f"{path}: top level is not a JSON object"
    has_configured = any(isinstance(doc.get(k), dict) for k in _CONFIGURED_KEYS)
    return True, True, has_configured, project_count, None
