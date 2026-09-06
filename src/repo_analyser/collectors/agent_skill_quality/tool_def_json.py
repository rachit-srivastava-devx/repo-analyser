"""Signal: MCP tool-definition JSON quality. An `mcp.json` file (or any
other JSON file that looks like one -- see discovery.py's
`_looks_like_mcp_tool_defs`) can declare MANY tool definitions, one per
`tools[]` entry.

`name` AND `inputSchema` must both be present for a valid schema;
`description` is explicitly OPTIONAL in the real protocol (confirmed
against this machine's installed `@modelcontextprotocol/sdk`'s own
shipped `spec.types.d.ts`: `interface Tool extends BaseMetadata` where
`BaseMetadata.name: string` and `Tool.inputSchema` are both required,
`description?: string` is not). That is exactly why description-
completeness is tracked as its own independent signal here rather than
folded into "valid schema" -- a protocol-valid MCP tool can still be
missing a description, which is a real triggering-accuracy smell, a
different question from "does this parse at all."

A real-world finding worth recording (AGENTS.md rule #2 -- verify, don't
guess): every real `mcp.json` found on this machine while building this
module (`~/.cursor/mcp.json`, a sibling project's own `mcp.json`, ...) is a
*server registry* (`{"mcpServers": {...}}`), not a static tool catalog --
the actual tool list for those is discovered live from each configured
server, never present in the file itself. So a well-formed `mcp.json` with
no top-level `tools` array is common and legitimate: it still counts as a
*found* agent-skill file (`skip_reason` stays empty), it just contributes
zero tool-def entries to grade from that file -- a true zero, not an
error, exactly parallel to a repo with a real 0% duplication score.
"""
from __future__ import annotations

import json
from pathlib import Path


def _grade_tool_def_json(path: Path) -> tuple[int, int, int]:
    """A tool-definition JSON file can declare MANY tool defs (one per
    `tools[]` entry). Returns (found, valid_schema, with_description)
    summed across every entry. Malformed JSON, or a `tools` key present
    but not a list, counts as one "found but not valid schema" file-level
    entry -- same non-crashing contract as `_grade_skill_md`. A
    well-formed file with no `tools` array at all (the real-world
    `mcp.json` server-registry shape, see module docstring) contributes
    nothing: not malformed, just zero declared tools to grade."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return 1, 0, 0
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return 1, 0, 0
    if not isinstance(data, dict):
        return 1, 0, 0
    tools = data.get("tools")
    if tools is None:
        return 0, 0, 0
    if not isinstance(tools, list):
        return 1, 0, 0
    found = valid = with_description = 0
    for entry in tools:
        found += 1
        if not isinstance(entry, dict):
            continue
        if "name" in entry and "inputSchema" in entry:
            valid += 1
        description = entry.get("description")
        if isinstance(description, str) and description.strip():
            with_description += 1
    return found, valid, with_description
