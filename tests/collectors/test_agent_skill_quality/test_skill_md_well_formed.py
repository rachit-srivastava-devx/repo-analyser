from __future__ import annotations

from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestSkillMdWellFormed:
    def test_name_and_description_present(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Does a thing well.\n---\n\n# My Skill\n"
        )
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 1
        assert result.tool_defs_with_description == 1
        assert result.skip_reason == ""

    def test_realistic_claude_skills_dir_layout(self, tmp_path: Path) -> None:
        # matches the real on-disk layout confirmed against
        # ~/.claude/skills/<name>/SKILL.md on this machine.
        repo = git_repo(tmp_path / "repo")
        skill_dir = repo / ".claude" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\ndescription: Does a thing.\n---\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 1
        assert result.skip_reason == ""
