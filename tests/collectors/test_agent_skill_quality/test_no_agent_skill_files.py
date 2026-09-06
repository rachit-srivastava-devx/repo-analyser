from __future__ import annotations

import json
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestNoAgentSkillFiles:
    def test_skip_reason_when_nothing_found(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "main.py").write_text("x = 1\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 0
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 0
        assert result.skip_reason  # non-empty

    def test_unrelated_tools_key_not_misdetected(self, tmp_path: Path) -> None:
        # a "tools" array of plain strings (e.g. a lint-tool-name list) is
        # not an MCP tool-definition file -- entries don't look tool-shaped.
        repo = git_repo(tmp_path / "repo")
        (repo / "build-config.json").write_text(json.dumps({"tools": ["eslint", "prettier"]}))
        result = analyze_repo(repo)
        assert result.skip_reason
