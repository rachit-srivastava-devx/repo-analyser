from __future__ import annotations

import csv
from pathlib import Path

from repo_analyser.collectors.design_docs import run_design_docs
from repo_analyser.core.util import read_json

from ._design_docs_helpers import ADR_ACCEPTED, commit_all, init_repo, write


def test_run_writes_csv_and_summary_for_mixed_portfolio(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "repos" / "a")
    write(repo_a, "docs/adr/0001-accepted.md", ADR_ACCEPTED)
    commit_all(repo_a, "add adr")

    repo_b = init_repo(tmp_path / "repos" / "b")
    write(repo_b, "README.md", "hi")
    commit_all(repo_b, "init")

    out_dir = tmp_path / "out"
    out_path = run_design_docs([repo_a, repo_b], out_dir)

    assert out_path.name == "design_docs.csv"
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["repo"] for r in rows} == {"a", "b"}
    a_row = next(r for r in rows if r["repo"] == "a")
    b_row = next(r for r in rows if r["repo"] == "b")
    assert a_row["has_adr_dir"] == "True"
    assert b_row["has_adr_dir"] == "False"
    assert b_row["skip_reason"] != ""

    summary = read_json(out_dir / "design_docs_summary.json")
    assert summary["repos_total"] == 2
    assert summary["repos_with_adr_dir"] == 1
    assert summary["adr_file_total"] == 1


def test_run_with_empty_repo_list(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_path = run_design_docs([], out_dir)
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []
