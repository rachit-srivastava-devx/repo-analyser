from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestMcpJsonMissingDescription:
    def test_one_tool_missing_description(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({
            "tools": [
                {"name": "get_weather", "description": "Get current weather.",
                 "inputSchema": {"type": "object"}},
                {"name": "get_time", "inputSchema": {"type": "object"}},
            ]
        }))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 2
        assert result.tool_defs_valid_schema == 2  # both structurally valid (name + inputSchema)
        assert result.tool_defs_with_description == 1  # only one has a real description
