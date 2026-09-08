from __future__ import annotations

import json
from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, markdown_cell, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestEdgeCases:
    def test_notebook_with_zero_code_cells_is_not_flagged_for_anything(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "readme.ipynb").write_text(nb([markdown_cell(["# Just prose, no code cells\n"])]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_nonlinear_execution == 0
        assert result.notebooks_unparseable == 0

    def test_code_cell_missing_outputs_and_execution_count_keys_entirely(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        sparse_cell = {"cell_type": "code", "metadata": {}, "source": ["x = 1\n"]}
        (repo / "sparse.ipynb").write_text(
            json.dumps({"cells": [sparse_cell], "nbformat": 4, "nbformat_minor": 5})
        )
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_unparseable == 0
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_nonlinear_execution == 0

    def test_ipynb_checkpoints_directory_is_excluded(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([code_cell(["x = 1\n"], execution_count=1)]))
        checkpoint_dir = repo / ".ipynb_checkpoints"
        checkpoint_dir.mkdir()
        (checkpoint_dir / "analysis-checkpoint.ipynb").write_text(
            nb([code_cell(["x = 1\n"], execution_count=1)])
        )
        result = analyze_repo(repo)
        assert result.notebooks_total == 1

    def test_source_as_single_string_instead_of_list_of_lines(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        cell = {
            "cell_type": "code", "execution_count": 1, "metadata": {}, "outputs": [],
            "source": "aws_key = 'AKIAABCDEFGHIJKLMNOP'",
        }
        (repo / "analysis.ipynb").write_text(json.dumps({"cells": [cell], "nbformat": 4, "nbformat_minor": 5}))
        result = analyze_repo(repo)
        assert result.notebooks_with_suspected_secrets == 1
