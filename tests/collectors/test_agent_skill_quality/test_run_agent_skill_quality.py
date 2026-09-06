from __future__ import annotations

import csv
from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import run_agent_skill_quality


class TestRunAgentSkillQuality:
    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_agent_skill_quality([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "tool_defs_found", "tool_defs_valid_schema",
            "tool_defs_with_description", "skip_reason",
        }
        assert rows[0]["tool_defs_found"] == "1"

    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_agent_skill_quality([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []
