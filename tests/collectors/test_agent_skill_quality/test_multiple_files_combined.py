from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestMultipleFilesCombined:
    def test_skill_md_and_mcp_json_both_counted(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\nname: my-skill\ndescription: Does a thing.\n---\n")
        (repo / "mcp.json").write_text(json.dumps({
            "tools": [{"name": "x", "description": "y", "inputSchema": {"type": "object"}}]
        }))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 2
        assert result.tool_defs_valid_schema == 2
        assert result.tool_defs_with_description == 2
