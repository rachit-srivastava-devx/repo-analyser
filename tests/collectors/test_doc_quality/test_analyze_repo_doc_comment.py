from __future__ import annotations

import json
from pathlib import Path

import pytest
from _doc_quality_helpers import HAS_INTERROGATE, commit, init_repo, lightweight_tag

from repo_analyser.collectors.doc_quality import analyze_repo


class TestAnalyzeRepoDocCommentHalf:
    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_python_repo_measures_real_interrogate_coverage(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(
            repo, "a.py",
            '"""Doc."""\n\n\ndef documented():\n    """Doc."""\n    return 1\n\n\n'
            'def undocumented():\n    return 2\n',
            date="2026-01-01T00:00:00",
        )
        result = analyze_repo(repo)
        assert result.doc_comment_tool == "interrogate"
        # Verified live against interrogate 1.7.0: the module docstring
        # itself is a third, separately-scored item alongside the two
        # functions (module=covered, documented=covered, undocumented=
        # missed) -- 2/3 covered, not 1/2. Confirmed with a standalone
        # `interrogate --no-color --fail-under 0 -vv .` run against this
        # exact file content.
        assert result.doc_comment_coverage_pct == 66.7
        assert result.skip_reason == ""

    def test_js_repo_with_eslint_plugin_jsdoc_is_detected(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        (repo / "package.json").write_text(
            json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^48.0.0"}}))
        (repo / ".eslintrc.json").write_text(json.dumps({"extends": ["plugin:jsdoc/recommended"]}))
        commit(repo, "index.js", "console.log('hi');\n", date="2026-01-01T00:00:00")
        result = analyze_repo(repo)
        assert result.doc_comment_tool == "eslint-plugin-jsdoc"
        assert result.doc_comment_coverage_pct == 0.0
        assert result.skip_reason == ""

    def test_js_repo_without_eslint_plugin_jsdoc_names_the_gap(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        (repo / "package.json").write_text(json.dumps({"devDependencies": {}}))
        commit(repo, "index.js", "console.log('hi');\n", date="2026-01-01T00:00:00")
        result = analyze_repo(repo)
        assert result.doc_comment_tool == ""
        assert "eslint-plugin-jsdoc" in result.skip_reason

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_go_only_repo_skips_doc_comment_half_but_not_changelog_half(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "main.go", "package main\n\nfunc main() {}\n", date="2026-01-01T00:00:00")
        # Heading date matches the commit date: a lightweight tag's own
        # creatordate resolves to its pointed commit's committer date
        # (confirmed live via `git for-each-ref --format=%(creatordate:short)`
        # -- see changelog_staleness.py's docstring), so tagging this same
        # commit gives the tag the identical 2026-01-02 date. A heading
        # dated a day earlier than the tagged commit would make this a
        # genuinely-stale case instead of the "freshly updated" case this
        # test means to exercise.
        commit(
            repo, "CHANGELOG.md",
            "# Changelog\n\n## [1.0.0] - 2026-01-02\n- initial release\n",
            date="2026-01-02T00:00:00",
        )
        lightweight_tag(repo, "v1.0.0")
        result = analyze_repo(repo)
        # doc-comment half: explicit, named gap -- not a silent zero.
        assert result.doc_comment_coverage_pct == 0.0
        assert result.doc_comment_tool == ""
        assert result.skip_reason == "no keyless scriptable doc-coverage-percentage tool for this language yet"
        # changelog half: fully, independently computed -- NOT blanked out
        # just because the doc-comment half was skipped.
        assert result.has_changelog is True
        assert result.changelog_last_entry_date == "2026-01-02"
        assert result.changelog_stale_vs_latest_tag == "not_stale"

    def test_rust_only_repo_names_the_same_gap(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "main.rs", "fn main() {}\n", date="2026-01-01T00:00:00")
        result = analyze_repo(repo)
        assert result.skip_reason == "no keyless scriptable doc-coverage-percentage tool for this language yet"
