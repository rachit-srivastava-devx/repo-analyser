from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestOtherJsonToolDefinitionFile:
    def test_non_mcp_json_named_file_with_tools_array_is_detected(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "tools.json").write_text(json.dumps({
            "tools": [{"name": "x", "description": "y", "inputSchema": {"type": "object"}}]
        }))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 1
        assert result.skip_reason == ""

    def test_non_mcp_json_named_file_with_empty_tools_array_is_ignored(self, tmp_path: Path) -> None:
        # unlike a literal mcp.json (a candidate by filename alone), a
        # differently-named file only earns candidate status by looking
        # tool-def-shaped -- an empty array doesn't look like anything.
        repo = git_repo(tmp_path / "repo")
        (repo / "tools.json").write_text(json.dumps({"tools": []}))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.skip_reason  # nothing agent-skill-shaped found at all

    def test_non_mcp_json_named_file_with_malformed_json_is_ignored(self, tmp_path: Path) -> None:
        # can't tell it was ever meant as a tool-def file if it doesn't
        # even parse -- unlike mcp.json, whose filename alone is the signal.
        repo = git_repo(tmp_path / "repo")
        (repo / "tools.json").write_text("{not valid json")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.skip_reason

    def test_non_mcp_json_named_file_whose_top_level_json_is_not_an_object(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "tools.json").write_text(json.dumps(["a", "b"]))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.skip_reason
