from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.doc_quality.changelog_parse import (
    _find_changelog,
    parse_changelog_last_entry_date,
)


class TestParseChangelogLastEntryDate:
    def test_finds_first_dated_heading(self) -> None:
        text = "# Changelog\n\n## [1.2.0] - 2026-03-15\n### Added\n- thing\n"
        assert parse_changelog_last_entry_date(text) == "2026-03-15"

    def test_skips_unreleased_placeholder_with_no_date(self) -> None:
        text = "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n"
        assert parse_changelog_last_entry_date(text) == "2026-01-01"

    def test_returns_empty_when_no_heading_has_a_date(self) -> None:
        text = "# Changelog\n\n## v1.2.0\n- did stuff, no date anywhere\n"
        assert parse_changelog_last_entry_date(text) == ""

    def test_returns_empty_for_empty_text(self) -> None:
        assert parse_changelog_last_entry_date("") == ""

    def test_ignores_dates_in_body_text_not_in_a_heading(self) -> None:
        # a date mentioned in prose before any real dated heading must not
        # be mistaken for the changelog's own last-entry date.
        text = "# Changelog\n\nReleased first on 2020-01-01, see history.\n\n## [1.0.0] - 2026-05-01\n"
        assert parse_changelog_last_entry_date(text) == "2026-05-01"


class TestFindChangelog:
    def test_finds_changelog_md_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
        found = _find_changelog(tmp_path)
        assert found is not None
        assert found.name == "CHANGELOG.md"

    def test_finds_history_md(self, tmp_path: Path) -> None:
        (tmp_path / "history.md").write_text("# History\n")
        assert _find_changelog(tmp_path) is not None

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        assert _find_changelog(tmp_path) is None

    def test_unrelated_markdown_files_are_not_mistaken_for_a_changelog(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi\n")
        assert _find_changelog(tmp_path) is None
