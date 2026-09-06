from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codeowners_health import analyze_repo

from ._codeowners_health_helpers import _git_repo, _stage_all


class TestNoCodeownersPresent:
    def test_no_codeowners_file_anywhere_is_a_valid_result_not_a_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "a.py").write_text("print('a')\n")
        (repo / "b.py").write_text("print('b')\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        assert result.has_codeowners is False
        assert result.codeowners_path is None
        assert result.total_tracked_files == 2
        assert result.owned_file_count == 0
        assert result.coverage_pct == 0.0
        assert result.unowned_file_count == 2
        assert result.distinct_owners == 0
        assert result.stale_rule_count == 0

    def test_no_codeowners_and_no_tracked_files(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")

        result = analyze_repo(repo)

        assert result.has_codeowners is False
        assert result.total_tracked_files == 0
        assert result.coverage_pct == 0.0


class TestCodeownersPrecedenceOrder:
    def test_github_codeowners_wins_over_root_and_docs(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / ".github").mkdir()
        (repo / ".github" / "CODEOWNERS").write_text("* @github-owner\n")
        (repo / "CODEOWNERS").write_text("* @root-owner\n")
        (repo / "docs").mkdir()
        (repo / "docs" / "CODEOWNERS").write_text("* @docs-owner\n")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        assert result.has_codeowners is True
        assert result.codeowners_path == ".github/CODEOWNERS"

    def test_root_codeowners_wins_over_docs_when_github_absent(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text("* @root-owner\n")
        (repo / "docs").mkdir()
        (repo / "docs" / "CODEOWNERS").write_text("* @docs-owner\n")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        assert result.codeowners_path == "CODEOWNERS"

    def test_docs_codeowners_used_when_only_one_present(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "docs").mkdir()
        (repo / "docs" / "CODEOWNERS").write_text("* @docs-owner\n")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)

        result = analyze_repo(repo)

        assert result.codeowners_path == "docs/CODEOWNERS"
