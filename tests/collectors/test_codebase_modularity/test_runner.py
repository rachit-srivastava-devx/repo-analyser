from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.codebase_modularity import run_codebase_modularity

from ._codebase_modularity_helpers import class_with_method_count, commit_all, init_repo, write


def test_writes_csv_header_even_for_zero_repos(tmp_path: Path) -> None:
    out_path = run_codebase_modularity([], tmp_path / "out")
    with out_path.open() as f:
        rows = list(csv.DictReader(f))
    assert rows == []
    with out_path.open() as f:
        header = f.readline().strip().split(",")
    assert "oversized_file_count" in header
    assert "god_class_language_supported" in header
    assert "layering_tool_detected" in header
    assert "skip_reason" in header


def test_writes_one_row_per_repo_and_summary_json(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "big.py", "\n".join(f"x{i} = {i}" for i in range(600)) + "\n")
    write(repo, "godclass.py", class_with_method_count("Big", 25))
    write(repo, ".importlinter", "[importlinter]\n")
    commit_all(repo, "init")

    out_path = run_codebase_modularity([repo], tmp_path / "out")
    with out_path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["repo"] == "r"
    assert int(rows[0]["oversized_file_count"]) == 1
    assert int(rows[0]["god_class_count"]) == 1
    assert rows[0]["layering_tool_detected"] == "import-linter"

    summary = json.loads((tmp_path / "out" / "codebase_modularity_summary.json").read_text())
    assert summary["repos_total"] == 1
    assert summary["repos_with_oversized_files"] == 1
    assert summary["oversized_files_total"] == 1
    assert summary["god_classes_total"] == 1
    assert summary["repos_with_layering_enforcement"] == 1
