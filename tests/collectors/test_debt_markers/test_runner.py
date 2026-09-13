from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.debt_markers.runner import run_debt_markers

from ._debt_markers_helpers import commit_all, init_repo, write


def test_run_debt_markers_on_empty_repo_list_writes_header_only_csv(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_path = run_debt_markers([], out_dir)

    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []

    summary = json.loads((out_dir / "debt_markers_summary.json").read_text())
    assert summary["repos_total"] == 0
    assert summary["total_markers"] == 0


def test_run_debt_markers_writes_csv_and_summary_for_a_real_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "a.py", "# TODO: one\n# FIXME: two\n")
    commit_all(repo, "init")

    out_dir = tmp_path / "out"
    out_path = run_debt_markers([repo], out_dir)

    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["repo"] == repo.name
    assert rows[0]["total_marker_count"] == "2"
    assert rows[0]["marker_counts_by_type"] == "FIXME:1;TODO:1"

    summary = json.loads((out_dir / "debt_markers_summary.json").read_text())
    assert summary["repos_total"] == 1
    assert summary["repos_skipped"] == 0
    assert summary["total_markers"] == 2
    assert summary["repos_with_markers"] == 1


def test_run_debt_markers_portfolio_summary_counts_skipped_repos(tmp_path: Path) -> None:
    good_repo = init_repo(tmp_path / "good")
    write(good_repo, "a.py", "# HACK: debt here\n")
    commit_all(good_repo, "init")

    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()

    out_dir = tmp_path / "out"
    run_debt_markers([good_repo, not_a_repo], out_dir)

    summary = json.loads((out_dir / "debt_markers_summary.json").read_text())
    assert summary["repos_total"] == 2
    assert summary["repos_skipped"] == 1
    assert summary["total_markers"] == 1
