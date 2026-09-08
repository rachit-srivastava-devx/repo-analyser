from __future__ import annotations

import csv
from pathlib import Path

from repo_analyser.collectors.api_contract import run_api_contract
from repo_analyser.core.util import read_json

from ._api_contract_helpers import OPENAPI_MIN, write


def test_run_writes_csv_and_summary_for_mixed_portfolio(tmp_path: Path) -> None:
    repo_a = tmp_path / "repos" / "a"
    repo_b = tmp_path / "repos" / "b"
    write(repo_a, "openapi.yaml", OPENAPI_MIN)
    repo_b.mkdir(parents=True)
    out_dir = tmp_path / "out"

    out_path = run_api_contract([repo_a, repo_b], out_dir)

    assert out_path.name == "api_contract.csv"
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["repo"] for r in rows} == {"a", "b"}
    a_row = next(r for r in rows if r["repo"] == "a")
    b_row = next(r for r in rows if r["repo"] == "b")
    assert a_row["has_spec"] == "True"
    assert b_row["has_spec"] == "False"
    assert b_row["skip_reason"] != ""

    summary = read_json(out_dir / "api_contract_summary.json")
    assert summary["repos_total"] == 2
    assert summary["repos_with_spec"] == 1


def test_run_with_empty_repo_list(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_path = run_api_contract([], out_dir)
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []
