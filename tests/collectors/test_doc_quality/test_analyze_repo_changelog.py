from __future__ import annotations

from pathlib import Path

from _doc_quality_helpers import commit, init_repo, lightweight_tag

from repo_analyser.collectors.doc_quality import analyze_repo


class TestAnalyzeRepoChangelogHalf:
    def test_repo_with_no_changelog_at_all(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "a.py", '"""Doc."""\n', date="2026-01-01T00:00:00")
        result = analyze_repo(repo)
        assert result.has_changelog is False
        assert result.changelog_last_entry_date == ""
        assert result.changelog_stale_vs_latest_tag == "unknown"

    def test_repo_with_stale_changelog_vs_newer_tag(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(
            repo, "CHANGELOG.md",
            "# Changelog\n\n## [1.0.0] - 2026-01-01\n- initial release\n",
            date="2026-01-01T00:00:00",
        )
        lightweight_tag(repo, "v1.0.0")
        # repo keeps moving, but nobody updated the changelog for the new release.
        commit(repo, "feature.py", '"""New feature, undocumented in changelog."""\n', date="2026-06-01T00:00:00")
        lightweight_tag(repo, "v2.0.0")
        result = analyze_repo(repo)
        assert result.changelog_last_entry_date == "2026-01-01"
        assert result.changelog_stale_vs_latest_tag == "stale"

    def test_repo_with_no_git_tags_reports_unknown_not_not_stale(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(
            repo, "CHANGELOG.md",
            "# Changelog\n\n## [1.0.0] - 2026-01-01\n- initial release\n",
            date="2026-01-01T00:00:00",
        )
        result = analyze_repo(repo)
        assert result.has_changelog is True
        assert result.changelog_last_entry_date == "2026-01-01"
        # Genuinely uncomputable (no tag to compare against) -- must not be
        # silently reported as "not_stale", which would assert a
        # comparison that was never actually made.
        assert result.changelog_stale_vs_latest_tag == "unknown"
