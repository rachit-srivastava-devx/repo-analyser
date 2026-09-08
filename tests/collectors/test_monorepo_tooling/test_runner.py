from __future__ import annotations

import csv
from pathlib import Path

from repo_analyser.collectors.monorepo_tooling import run_monorepo_tooling
from repo_analyser.core.util import read_json

from ._monorepo_tooling_helpers import NX_CONFIGURED, TURBO_TASKS_SCHEMA, write


def test_run_writes_csv_and_summary_for_mixed_portfolio(tmp_path: Path) -> None:
    repo_a = tmp_path / "repos" / "a"
    repo_b = tmp_path / "repos" / "b"
    write(repo_a, "nx.json", NX_CONFIGURED)
    write(repo_b, "turbo.json", TURBO_TASKS_SCHEMA)
    out_dir = tmp_path / "out"

    out_path = run_monorepo_tooling([repo_a, repo_b], out_dir)

    assert out_path.name == "monorepo_tooling.csv"
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["repo"] for r in rows} == {"a", "b"}
    a_row = next(r for r in rows if r["repo"] == "a")
    b_row = next(r for r in rows if r["repo"] == "b")
    assert a_row["nx_present"] == "True"
    assert b_row["turbo_present"] == "True"

    summary = read_json(out_dir / "monorepo_tooling_summary.json")
    assert summary["repos_total"] == 2
    assert summary["repos_with_any_orchestrator"] == 2
    assert summary["repos_with_nx"] == 1
    assert summary["repos_with_turbo"] == 1
    assert summary["repos_with_multiple_orchestrators"] == 0


def test_run_with_empty_repo_list(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_path = run_monorepo_tooling([], out_dir)
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []
    summary = read_json(out_dir / "monorepo_tooling_summary.json")
    assert summary["repos_total"] == 0


def test_run_reports_plain_repo_with_none_found(tmp_path: Path) -> None:
    repo = tmp_path / "repos" / "plain"
    repo.mkdir(parents=True)
    out_dir = tmp_path / "out"

    out_path = run_monorepo_tooling([repo], out_dir)

    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["orchestrator_count"] == "0"
    assert rows[0]["skip_reason"] != ""
