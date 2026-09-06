from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.flag_debt import run_flag_debt

from ._flag_debt_helpers import _git_repo


class TestRunFlagDebt:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_flag_debt([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "app.py").write_text('is_enabled("some_flag")\n')
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_flag_debt([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "sdk_detected", "flags_referenced_count", "flags_defined_count",
            "orphaned_flag_definitions", "undefined_flag_references", "duplicate_definition_count",
        }
        assert rows[0]["flags_referenced_count"] == "1"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = _git_repo(tmp_path / "repo-a")
        repo_b = _git_repo(tmp_path / "repo-b")
        (repo_b / "app.py").write_text('import ldclient\nis_enabled("flag_b")\n')
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_flag_debt([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "flag_debt_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["repos_with_sdk_detected"] == 1
        assert summary["total_flags_referenced"] == 1
