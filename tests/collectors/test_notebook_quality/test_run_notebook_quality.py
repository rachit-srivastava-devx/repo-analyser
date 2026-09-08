from __future__ import annotations

import csv
from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, nb

from repo_analyser.collectors.notebook_quality import run_notebook_quality


class TestRunNotebookQuality:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_notebook_quality([], out_dir)
        with open(out_path) as f:
            assert list(csv.DictReader(f)) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([code_cell(["x = 1\n"], execution_count=1)]))
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_notebook_quality([repo], out_dir)
        with open(out_path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "notebooks_total", "notebooks_with_uncleared_outputs",
            "notebooks_with_suspected_secrets", "notebooks_nonlinear_execution",
            "notebooks_unparseable", "skip_reason",
        }
        assert rows[0]["notebooks_total"] == "1"

    def test_multiple_repos_mixed_notebooks_and_none(self, tmp_path: Path) -> None:
        repo_a = git_repo(tmp_path / "repo-a")
        (repo_a / "analysis.ipynb").write_text(nb([code_cell(["x = 1\n"], execution_count=1)]))
        repo_b = git_repo(tmp_path / "repo-b")
        (repo_b / "main.py").write_text("x = 1\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_notebook_quality([repo_a, repo_b], out_dir)
        with open(out_path) as f:
            rows = {r["repo"]: r for r in csv.DictReader(f)}
        assert rows["repo-a"]["notebooks_total"] == "1"
        assert rows["repo-b"]["notebooks_total"] == "0"
        assert rows["repo-b"]["skip_reason"] == "no .ipynb files found"
