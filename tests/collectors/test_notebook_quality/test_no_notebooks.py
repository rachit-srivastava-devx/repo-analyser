from __future__ import annotations

from pathlib import Path

from _notebook_quality_helpers import git_repo

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestNoNotebooks:
    def test_repo_with_no_ipynb_files_reports_skip_reason(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "main.py").write_text("x = 1\n")
        result = analyze_repo(repo)
        assert result.notebooks_total == 0
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_with_suspected_secrets == 0
        assert result.notebooks_nonlinear_execution == 0
        assert result.notebooks_unparseable == 0
        assert result.skip_reason == "no .ipynb files found"

    def test_completely_empty_repo(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        result = analyze_repo(repo)
        assert result.notebooks_total == 0
        assert result.skip_reason
