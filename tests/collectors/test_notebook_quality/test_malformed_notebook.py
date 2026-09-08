from __future__ import annotations

import json
from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestMalformedNotebook:
    def test_invalid_json_is_counted_as_unparseable_not_zero_notebooks(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "broken.ipynb").write_text("{not valid json")
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_unparseable == 1
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_with_suspected_secrets == 0
        assert result.notebooks_nonlinear_execution == 0
        assert result.skip_reason == ""

    def test_valid_json_missing_cells_key_is_counted_as_unparseable(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "broken.ipynb").write_text(json.dumps({"metadata": {}, "nbformat": 4, "nbformat_minor": 5}))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_unparseable == 1

    def test_cells_present_but_not_a_list_is_unparseable(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "broken.ipynb").write_text(json.dumps({"cells": "not-a-list", "nbformat": 4}))
        result = analyze_repo(repo)
        assert result.notebooks_unparseable == 1

    def test_top_level_json_array_not_object_is_unparseable(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "broken.ipynb").write_text(json.dumps([1, 2, 3]))
        result = analyze_repo(repo)
        assert result.notebooks_unparseable == 1

    def test_one_good_and_one_malformed_notebook_together(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "good.ipynb").write_text(nb([code_cell(["x = 1\n"], execution_count=1)]))
        (repo / "bad.ipynb").write_text("{not valid json")
        result = analyze_repo(repo)
        assert result.notebooks_total == 2
        assert result.notebooks_unparseable == 1
        assert result.notebooks_with_uncleared_outputs == 0

    def test_empty_but_present_cells_list_is_parseable_not_unparseable(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "blank.ipynb").write_text(json.dumps({"cells": [], "nbformat": 4, "nbformat_minor": 5}))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_unparseable == 0
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_nonlinear_execution == 0

    def test_non_dict_entries_inside_cells_do_not_crash(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        good_cell = code_cell(["aws_key = 'AKIAABCDEFGHIJKLMNOP'\n"], execution_count=1)
        notebook = {"cells": [good_cell, "not-a-cell", 42, None], "nbformat": 4, "nbformat_minor": 5}
        (repo / "corrupt.ipynb").write_text(json.dumps(notebook))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_unparseable == 0
        assert result.notebooks_with_suspected_secrets == 1
