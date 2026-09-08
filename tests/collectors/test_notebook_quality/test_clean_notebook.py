from __future__ import annotations

from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, markdown_cell, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestCleanNotebook:
    def test_cleared_outputs_monotonic_execution_no_secrets_flags_nothing(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            markdown_cell(["# Data Analysis\n", "\n", "Load and summarize the dataset.\n"]),
            code_cell(["import pandas as pd\n", "df = pd.read_csv('data.csv')\n"], execution_count=1),
            code_cell(["df.describe()\n"], execution_count=2),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_with_suspected_secrets == 0
        assert result.notebooks_nonlinear_execution == 0
        assert result.notebooks_unparseable == 0
        assert result.skip_reason == ""
