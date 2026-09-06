from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codeowners_health import analyze_repo
from repo_analyser.collectors.codeowners_health.matcher import pattern_matches

from ._codeowners_health_helpers import _git_repo, _stage_all


class TestPatternMatchesPrecedenceRules:
    def test_no_leading_slash_matches_at_any_depth(self) -> None:
        assert pattern_matches("*.py", "a.py")
        assert pattern_matches("*.py", "src/nested/deep/a.py")

    def test_leading_slash_anchors_to_repo_root(self) -> None:
        assert pattern_matches("/README.md", "README.md")
        assert not pattern_matches("/README.md", "src/README.md")

    def test_trailing_slash_matches_directory_contents_at_any_depth(self) -> None:
        assert pattern_matches("vendor/", "vendor/lib.py")
        assert pattern_matches("vendor/", "src/vendor/lib.py")
        assert not pattern_matches("vendor/", "vendor-lib/x.py")  # whole segment, not substring
        assert not pattern_matches("vendor/", "vendor")  # directory pattern needs a file strictly inside it

    def test_anchored_directory_pattern_combines_both_markers(self) -> None:
        assert pattern_matches("/build/", "build/out.js")
        assert not pattern_matches("/build/", "src/build/out.js")

    def test_anchored_pattern_wider_than_the_file_path_does_not_match(self) -> None:
        assert not pattern_matches("/src/deep/nested.py", "a.py")

    def test_multi_segment_pattern_with_no_leading_slash_still_matches_at_any_depth(self) -> None:
        assert pattern_matches("src/*.py", "a/src/b.py")
        assert not pattern_matches("src/*.py", "a/src/b.json")


class TestCoverageMathWithConcreteNumbers:
    def test_last_match_wins_and_full_coverage_arithmetic(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text(
            "*.py @default-owner\n"
            "*.py @py-team\n"
            "src/ @src-team\n"
            "old-deleted-dir/ @ghost-owner\n"
        )
        (repo / "a.py").write_text("x\n")
        (repo / "src").mkdir()
        (repo / "src" / "b.py").write_text("x\n")
        (repo / "src" / "nested").mkdir()
        (repo / "src" / "nested" / "c.py").write_text("x\n")
        (repo / "src" / "config.json").write_text("{}\n")
        (repo / "docs").mkdir()
        (repo / "docs" / "readme.md").write_text("x\n")
        (repo / "README.md").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        # 7 tracked files total (the 6 content files plus CODEOWNERS itself,
        # which _stage_all also adds to the index): a.py, src/b.py,
        # src/nested/c.py, src/config.json end up owned (src/ is declared
        # last, so it wins over *.py for the three files under src/ even
        # though *.py also matches them); docs/readme.md, README.md, and
        # CODEOWNERS itself match nothing and are unowned.
        assert result.total_tracked_files == 7
        assert result.owned_file_count == 4
        assert result.unowned_file_count == 3
        assert result.coverage_pct == 57.14
        # @default-owner's rule is always shadowed by the *.py rule below it,
        # so it never actually owns anything and must not be counted.
        assert result.distinct_owners == 2
        # only old-deleted-dir/ matches zero files
        assert result.stale_rule_count == 1

    def test_duplicate_identical_stale_patterns_each_count_independently(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text("ghost/ @nobody\nghost/ @nobody\n")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        assert result.stale_rule_count == 2  # each duplicate line counts on its own, not deduped
        assert result.owned_file_count == 0
        assert result.coverage_pct == 0.0


class TestRequiredEdgeCases:
    def test_empty_codeowners_file_zero_rules_zero_coverage(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text("")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        # 2 tracked files: a.py plus the (empty-content, but real and staged)
        # CODEOWNERS file itself.
        assert result.has_codeowners is True
        assert result.total_tracked_files == 2
        assert result.owned_file_count == 0
        assert result.coverage_pct == 0.0
        assert result.stale_rule_count == 0

    def test_codeowners_present_but_zero_tracked_files_is_zero_not_nan(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text("* @someone\n")
        # deliberately never staged: zero tracked files despite a real CODEOWNERS on disk

        result = analyze_repo(repo)

        assert result.has_codeowners is True
        assert result.total_tracked_files == 0
        assert result.owned_file_count == 0
        assert result.unowned_file_count == 0
        assert result.coverage_pct == 0.0
