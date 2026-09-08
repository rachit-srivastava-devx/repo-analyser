from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.migration_hygiene import run_migration_hygiene

from ._migration_hygiene_helpers import DJANGO_CREATE_MODEL, commit_all, init_repo, write


def test_writes_csv_header_even_for_zero_repos(tmp_path: Path) -> None:
    out_path = run_migration_hygiene([], tmp_path / "out")
    with out_path.open() as f:
        rows = list(csv.DictReader(f))
    assert rows == []
    with out_path.open() as f:
        header = f.readline().strip().split(",")
    assert "migration_convention" in header
    assert "skip_reason" in header


def test_writes_one_row_per_repo_and_summary_json(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "app/migrations/0001_initial.py", DJANGO_CREATE_MODEL)
    commit_all(repo, "init")

    out_path = run_migration_hygiene([repo], tmp_path / "out")
    with out_path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["repo"] == "r"
    assert rows[0]["migration_convention"] == "django"
    assert rows[0]["reversible_count"] == "1"

    summary = json.loads((tmp_path / "out" / "migration_hygiene_summary.json").read_text())
    assert summary["repos_total"] == 1
    assert summary["repos_with_recognized_convention"] == 1
