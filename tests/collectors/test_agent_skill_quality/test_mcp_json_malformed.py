from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestMcpJsonMalformed:
    def test_malformed_json_does_not_crash_the_collector(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text("{not valid json")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 0
        assert result.skip_reason == ""

    def test_empty_tools_array(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({"tools": []}))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.skip_reason == ""  # file exists, legitimately zero tools declared

    def test_tool_entry_that_is_not_a_dict(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({"tools": ["not-a-dict", 123]}))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 2
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 0

    def test_real_world_server_registry_shape_is_not_malformed(self, tmp_path: Path) -> None:
        # the actual common real-world mcp.json shape (confirmed against
        # ~/.cursor/mcp.json and others on this machine) -- a server
        # registry, not a static tool catalog. Valid JSON, zero declared
        # tools, not an error.
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({
            "mcpServers": {"github": {"url": "https://example.com/mcp"}}
        }))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.skip_reason == ""

    def test_top_level_json_is_not_an_object(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps(["not", "an", "object"]))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0

    def test_tools_key_present_but_not_a_list(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "mcp.json").write_text(json.dumps({"tools": "not-a-list"}))
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0
