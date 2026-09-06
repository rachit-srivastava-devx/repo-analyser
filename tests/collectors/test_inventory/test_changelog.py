from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from repo_analyser.collectors.inventory.changelog import (
    _find_changelog,
    _latest_dated_header,
    collect_changelog_signals,
)

from ._inventory_helpers import _commit_on_date, _git, _init_repo


class TestFindChangelog:
    @pytest.mark.parametrize("name", ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG", "HISTORY.md"])
    def test_finds_each_supported_name(self, tmp_path: Path, name: str) -> None:
        (tmp_path / name).write_text("stuff")
        found = _find_changelog(tmp_path)
        assert found is not None
        assert found.name == name

    @pytest.mark.parametrize("actual_name", ["changelog.md", "History.MD", "Changelog"])
    def test_case_insensitive_match(self, tmp_path: Path, actual_name: str) -> None:
        (tmp_path / actual_name).write_text("stuff")
        assert _find_changelog(tmp_path) is not None

    def test_absent_returns_none(self, tmp_path: Path) -> None:
        assert _find_changelog(tmp_path) is None

    def test_unrelated_files_do_not_match(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("stuff")
        assert _find_changelog(tmp_path) is None


class TestLatestDatedHeader:
    def test_keep_a_changelog_style(self) -> None:
        text = "# Changelog\n\n## [1.2.3] - 2024-01-15\n\nStuff.\n"
        assert _latest_dated_header(text) == date(2024, 1, 15)

    def test_v_prefixed_parenthesized_style(self) -> None:
        text = "## v1.2.3 (2024-03-10)\n\nStuff.\n"
        assert _latest_dated_header(text) == date(2024, 3, 10)

    def test_bare_date_on_header_line(self) -> None:
        text = "### 2024-05-20 release\n\nStuff.\n"
        assert _latest_dated_header(text) == date(2024, 5, 20)

    def test_takes_first_dated_header_not_last(self) -> None:
        # reverse-chronological changelogs list the newest entry first.
        text = "## [2.0.0] - 2024-06-01\n\n## [1.0.0] - 2023-01-01\n"
        assert _latest_dated_header(text) == date(2024, 6, 1)

    def test_no_dated_header_returns_none(self) -> None:
        # mirrors this real repo's own CHANGELOG.md header style.
        text = "## Unreleased\n\n## 0.2.0 -- rename\n\n## 0.1.0 -- initial release\n"
        assert _latest_dated_header(text) is None

    def test_date_only_in_body_not_on_header_line_is_ignored(self) -> None:
        text = "## Unreleased\n\nReleased on 2024-01-01 but not in the header.\n"
        assert _latest_dated_header(text) is None

    def test_malformed_date_is_skipped_in_favor_of_next_real_one(self) -> None:
        text = "## [2.0.0] - 2024-13-40\n\n## [1.0.0] - 2023-01-01\n"
        assert _latest_dated_header(text) == date(2023, 1, 1)


class TestCollectChangelogSignals:
    """The three None-triggering cases for changelog_staleness_days, each
    isolated in its own test, plus a positive end-to-end case."""

    def test_no_changelog_file_is_none(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        _commit_on_date(repo, "f.txt", "x", "init", "2024-01-01T00:00:00")
        _git(repo, "tag", "v1.0.0")  # tag exists -- isolates "no changelog" as the cause
        result = collect_changelog_signals(repo)
        assert result.changelog_present is False
        assert result.changelog_staleness_days is None

    def test_changelog_with_no_dated_entry_is_none(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        (repo / "CHANGELOG.md").write_text("## Unreleased\n\n## 0.1.0 -- initial\n")
        _commit_on_date(repo, "f.txt", "x", "init", "2024-01-01T00:00:00")
        _git(repo, "tag", "v1.0.0")  # tag exists -- isolates "no dated entry" as the cause
        result = collect_changelog_signals(repo)
        assert result.changelog_present is True
        assert result.changelog_last_entry_date is None
        assert result.changelog_staleness_days is None

    def test_no_tags_at_all_is_none(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        (repo / "CHANGELOG.md").write_text("## [1.0.0] - 2024-01-01\n")
        _commit_on_date(repo, "f.txt", "x", "init", "2024-01-01T00:00:00")
        # deliberately no tag created
        result = collect_changelog_signals(repo)
        assert result.changelog_present is True
        assert result.changelog_last_entry_date == "2024-01-01"
        assert result.latest_tag_date is None
        assert result.changelog_staleness_days is None

    def test_present_dated_and_tagged_computes_real_staleness(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        (repo / "CHANGELOG.md").write_text("## [1.0.0] - 2024-01-01\n")
        _commit_on_date(repo, "f.txt", "x", "init", "2024-01-01T00:00:00")
        _commit_on_date(repo, "f.txt", "y", "release commit", "2024-01-11T00:00:00")
        _git(repo, "tag", "v1.0.0")
        result = collect_changelog_signals(repo)
        assert result.changelog_present is True
        assert result.changelog_last_entry_date == "2024-01-01"
        assert result.latest_tag_date == "2024-01-11"
        assert result.changelog_staleness_days == 10
