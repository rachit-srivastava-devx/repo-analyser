"""Data shape and constants shared across agent_skill_quality's submodules."""
from __future__ import annotations

from dataclasses import dataclass

# The signature keys that distinguish a real MCP tool-definition entry from
# an unrelated "tools": [...] array in some other config (e.g. a plain
# list of lint-tool names) -- any one of these on a dict entry is enough to
# treat the file as a genuine tool-definition candidate.
_TOOL_ENTRY_SIGNATURE_KEYS = {"name", "description", "inputSchema"}


@dataclass
class AgentSkillQualityResult:
    repo: str
    tool_defs_found: int
    tool_defs_valid_schema: int
    tool_defs_with_description: int
    skip_reason: str
