from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestMcpJsonWellFormed:
    def test_all_tools_have_descriptions(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({
            "tools": [
                {"name": "get_weather", "description": "Get current weather.",
                 "inputSchema": {"type": "object", "properties": {}}},
                {"name": "get_time", "description": "Get current time.",
                 "inputSchema": {"type": "object", "properties": {}}},
            ]
        }))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 2
        assert result.tool_defs_valid_schema == 2
        assert result.tool_defs_with_description == 2
        assert result.skip_reason == ""
