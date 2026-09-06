"""Finding candidate agent-skill / tool-definition files on disk. No
grading here -- see skill_md.py and tool_def_json.py for that.

No external tool -- pure filesystem/parsing, the same shape as
inventory.py. Detection reuses repo_type.py's own `_content_agent_skills`
glob patterns (SKILL.md / mcp.json by filename, tree-wide), reimplemented
locally per this codebase's no-cross-collector-private-import convention;
that module only checks *presence*, this package grades what's actually
inside.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from .models import _TOOL_ENTRY_SIGNATURE_KEYS


def _tracked_files(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*")
            if p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)]


def _looks_like_mcp_tool_defs(data: object) -> bool:
    """True when a JSON file's top-level shape is recognizably an MCP
    `tools/list`-style response: a non-empty `tools` array with at least
    one entry carrying a name/description/inputSchema-shaped key. This is
    the detection bar for files NOT literally named `mcp.json` (which are
    always treated as a candidate on filename alone, matching
    repo_type.py's own signal) -- it guards against an unrelated
    "tools": [...] key in some other config being misidentified as an
    agent tool-definition file."""
    if not isinstance(data, dict):
        return False
    tools = data.get("tools")
    if not isinstance(tools, list) or not tools:
        return False
    return any(isinstance(entry, dict) and (_TOOL_ENTRY_SIGNATURE_KEYS & entry.keys())
               for entry in tools)


def _find_other_tool_def_json_files(files: list[Path]) -> list[Path]:
    """JSON files not literally named `mcp.json` that still look like an
    MCP tool-definition file per `_looks_like_mcp_tool_defs` -- e.g. a
    statically checked-in `tools.json` snapshot of a server's own
    `tools/list` response. Parsed once here purely for detection; grading
    re-parses (matches this codebase's existing precedent of
    repo_type.py's own content detectors independently re-reading
    package.json per concern rather than sharing parsed state)."""
    candidates = []
    for p in files:
        if p.suffix != ".json" or p.name == "mcp.json":
            continue
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        if _looks_like_mcp_tool_defs(data):
            candidates.append(p)
    return candidates
