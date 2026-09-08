from __future__ import annotations

from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestNonlinearExecution:
    def test_decreasing_execution_count_is_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["print('first cell, run last')\n"], execution_count=5),
            code_cell(["print('second cell, run first')\n"], execution_count=1),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_nonlinear_execution == 1
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_with_suspected_secrets == 0

    def test_monotonic_increasing_is_not_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["a = 1\n"], execution_count=1),
            code_cell(["b = 2\n"], execution_count=2),
            code_cell(["c = 3\n"], execution_count=3),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_nonlinear_execution == 0

    def test_repeated_execution_count_is_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["a = 1\n"], execution_count=1),
            code_cell(["b = 2\n"], execution_count=1),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_nonlinear_execution == 1
