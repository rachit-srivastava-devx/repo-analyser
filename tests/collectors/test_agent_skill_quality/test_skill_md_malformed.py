from __future__ import annotations

from pathlib import Path

from _agent_skill_quality_helpers import git_repo

from repo_analyser.collectors.agent_skill_quality import analyze_repo


class TestSkillMdMalformed:
    def test_missing_frontmatter_entirely(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("# Just a heading, no frontmatter\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 0
        assert result.skip_reason == ""  # found (if broken), not "nothing found"

    def test_frontmatter_block_never_closes(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\nname: my-skill\ndescription: no closing delimiter\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0

    def test_missing_name_key_but_has_description(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\ndescription: has description, no name\n---\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 1  # description alone is still gradeable

    def test_empty_description_value(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\nname: my-skill\ndescription:\n---\n")
        result = analyze_repo(repo)
        assert result.tool_defs_valid_schema == 1  # both keys present
        assert result.tool_defs_with_description == 0  # but the value is empty

    def test_invalid_yaml_in_frontmatter_does_not_crash(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\nname: [unclosed\n---\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0

    def test_frontmatter_that_parses_to_a_non_dict(self, tmp_path: Path) -> None:
        # "---\n- a\n- b\n---\n" is valid YAML, but a list, not a mapping --
        # there is no "name"/"description" key to even look for.
        repo = git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("---\n- a\n- b\n---\n")
        result = analyze_repo(repo)
        assert result.tool_defs_found == 1
        assert result.tool_defs_valid_schema == 0
        assert result.tool_defs_with_description == 0
