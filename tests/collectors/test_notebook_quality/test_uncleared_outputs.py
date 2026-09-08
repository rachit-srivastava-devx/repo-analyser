from __future__ import annotations

from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestUnclearedOutputs:
    def test_code_cell_with_nonempty_outputs_is_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["import pandas as pd\n"], execution_count=1),
            code_cell(
                ["df.describe()\n"], execution_count=2,
                outputs=[{
                    "data": {"text/plain": ["       col1\n", "count  10.0\n"]},
                    "execution_count": 2, "metadata": {}, "output_type": "execute_result",
                }],
            ),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_with_uncleared_outputs == 1
        assert result.notebooks_with_suspected_secrets == 0
        assert result.notebooks_nonlinear_execution == 0

    def test_empty_outputs_list_is_not_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([code_cell(["x = 1\n"], execution_count=1, outputs=[])]))
        result = analyze_repo(repo)
        assert result.notebooks_with_uncleared_outputs == 0

    def test_only_flags_once_per_notebook_even_with_multiple_dirty_cells(self, tmp_path: Path) -> None:
        stream_output = [{"name": "stdout", "output_type": "stream", "text": ["hi\n"]}]
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["print('a')\n"], execution_count=1, outputs=stream_output),
            code_cell(["print('b')\n"], execution_count=2, outputs=stream_output),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_with_uncleared_outputs == 1
