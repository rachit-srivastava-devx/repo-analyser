from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codeowners_health.parser import (
    CodeownersRule,
    find_codeowners,
    parse_codeowners,
)


class TestFindCodeowners:
    def test_returns_none_when_nothing_present(self, tmp_path: Path) -> None:
        assert find_codeowners(tmp_path) is None


class TestParseCodeownersEdgeCases:
    def test_empty_file_yields_zero_rules(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("")
        assert parse_codeowners(p) == []

    def test_blank_lines_and_full_line_comments_are_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("\n# a full-line comment\n\n*.py @alice\n")

        rules = parse_codeowners(p)

        assert rules == [CodeownersRule(pattern="*.py", owners=("@alice",), line_number=4)]

    def test_inline_comment_is_stripped_from_a_content_line(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("*.py @alice  # python files\n")

        rules = parse_codeowners(p)

        assert rules == [CodeownersRule(pattern="*.py", owners=("@alice",), line_number=1)]

    def test_multiple_owners_on_one_line(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("*.py @alice @bob team@example.com\n")

        rules = parse_codeowners(p)

        assert rules[0].owners == ("@alice", "@bob", "team@example.com")

    def test_pattern_with_no_owners_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("*.py @alice\n*.md\n*.go @carol\n")

        rules = parse_codeowners(p)

        assert [r.pattern for r in rules] == ["*.py", "*.go"]

    def test_duplicate_identical_pattern_lines_produce_two_independent_rules(self, tmp_path: Path) -> None:
        p = tmp_path / "CODEOWNERS"
        p.write_text("*.py @alice\n*.py @bob\n")

        rules = parse_codeowners(p)

        assert len(rules) == 2
        assert rules[0].pattern == rules[1].pattern == "*.py"
        assert rules[0].owners == ("@alice",)
        assert rules[1].owners == ("@bob",)
        assert rules[0].line_number == 1
        assert rules[1].line_number == 2
