from __future__ import annotations

from pathlib import Path

from _doc_quality_helpers import commit, git, init_repo, lightweight_tag

from repo_analyser.collectors.doc_quality.changelog_staleness import (
    _changelog_staleness,
    latest_tag_and_date,
)


class TestChangelogStaleness:
    def test_stale_when_changelog_older_than_tag(self) -> None:
        assert _changelog_staleness("2026-01-01", "2026-06-01") == "stale"

    def test_not_stale_when_changelog_newer_than_tag(self) -> None:
        assert _changelog_staleness("2026-06-01", "2026-01-01") == "not_stale"

    def test_not_stale_when_changelog_same_date_as_tag(self) -> None:
        assert _changelog_staleness("2026-01-01", "2026-01-01") == "not_stale"

    def test_unknown_when_no_tag_date(self) -> None:
        # must NOT be "not_stale" -- no tag means the comparison was never
        # actually made, a distinct fact from "checked and found fresh".
        assert _changelog_staleness("2026-01-01", None) == "unknown"

    def test_unknown_when_no_changelog_date(self) -> None:
        assert _changelog_staleness("", "2026-01-01") == "unknown"

    def test_unknown_when_neither_present(self) -> None:
        assert _changelog_staleness("", None) == "unknown"


class TestLatestTagAndDate:
    def test_no_tags_returns_none(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "a.txt", "a\n", date="2026-01-01T00:00:00")
        assert latest_tag_and_date(repo) is None

    def test_single_tag_returns_its_name_and_date(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "a.txt", "a\n", date="2026-01-01T00:00:00")
        lightweight_tag(repo, "v1.0.0")
        result = latest_tag_and_date(repo)
        assert result == ("v1.0.0", "2026-01-01")

    def test_newest_by_creation_date_wins_not_alphabetical_sort(self, tmp_path: Path) -> None:
        # "v10.0.0" < "v9.0.0" alphabetically, but v10.0.0 is tagged later
        # (newer creatordate) and must still be picked -- this is exactly
        # why `--sort=-creatordate` is used instead of sorting tag names.
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "a.txt", "a\n", date="2026-01-01T00:00:00")
        lightweight_tag(repo, "v9.0.0")
        commit(repo, "b.txt", "b\n", date="2026-06-01T00:00:00")
        lightweight_tag(repo, "v10.0.0")
        assert latest_tag_and_date(repo) == ("v10.0.0", "2026-06-01")

    def test_annotated_tag_creatordate_is_the_tag_objects_own_date(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "a.txt", "a\n", date="2026-01-01T00:00:00")
        git(repo, "tag", "-a", "v1.0.0", "-m", "release", date="2026-03-01T00:00:00")
        assert latest_tag_and_date(repo) == ("v1.0.0", "2026-03-01")
