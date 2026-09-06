"""Per-repo orchestration: combines both tool-definition signals (SKILL.md
and tool-def JSON) into one result.

Two different kinds of file get graded under one shared "tool definition"
concept, matching the checklist's own "tools with vs. without a
description" framing: a `SKILL.md` file IS one tool definition (see
skill_md.py); an `mcp.json` file (or another JSON file shaped like an MCP
`tools/list` response, see discovery.py) can declare MANY tool
definitions, one per array entry (see tool_def_json.py).

The structural-validity bar is deliberately NOT the same for both, because
the two formats' own real specs disagree about what's required -- see
skill_md.py and tool_def_json.py for each format's own bar and the
evidence behind it.
"""
from __future__ import annotations

from pathlib import Path

from .discovery import _find_other_tool_def_json_files, _tracked_files
from .models import AgentSkillQualityResult
from .skill_md import _grade_skill_md
from .tool_def_json import _grade_tool_def_json


def analyze_repo(repo: Path) -> AgentSkillQualityResult:
    files = _tracked_files(repo)
    skill_md_files = [p for p in files if p.name == "SKILL.md"]
    mcp_json_files = [p for p in files if p.name == "mcp.json"]
    other_tool_def_files = _find_other_tool_def_json_files(files)

    if not skill_md_files and not mcp_json_files and not other_tool_def_files:
        return AgentSkillQualityResult(
            repo=repo.name, tool_defs_found=0, tool_defs_valid_schema=0,
            tool_defs_with_description=0,
            skip_reason="no SKILL.md, mcp.json, or MCP tool-definition JSON files found",
        )

    found = valid = with_description = 0
    for p in skill_md_files:
        f, v, d = _grade_skill_md(p)
        found += f
        valid += v
        with_description += d
    for p in mcp_json_files + other_tool_def_files:
        f, v, d = _grade_tool_def_json(p)
        found += f
        valid += v
        with_description += d

    return AgentSkillQualityResult(
        repo=repo.name, tool_defs_found=found, tool_defs_valid_schema=valid,
        tool_defs_with_description=with_description, skip_reason="",
    )
