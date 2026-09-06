from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.codeowners_health import run_codeowners_health

from ._codeowners_health_helpers import _git_repo, _stage_all


class TestRunCodeownersHealth:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_codeowners_health([], out_dir)

        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "CODEOWNERS").write_text("* @team\n")
        (repo / "a.py").write_text("x\n")
        _stage_all(repo)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_codeowners_health([repo], out_dir)

        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "has_codeowners", "codeowners_path", "total_tracked_files",
            "owned_file_count", "coverage_pct", "unowned_file_count",
            "distinct_owners", "stale_rule_count",
        }
        assert rows[0]["has_codeowners"] == "True"
        assert rows[0]["coverage_pct"] == "100.0"
        assert rows[0]["codeowners_path"] == "CODEOWNERS"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = _git_repo(tmp_path / "repo-a")
        (repo_a / "a.py").write_text("x\n")
        _stage_all(repo_a)  # no CODEOWNERS -- 0.0% coverage

        repo_b = _git_repo(tmp_path / "repo-b")
        (repo_b / "CODEOWNERS").write_text("* @team\n")
        (repo_b / "b.py").write_text("x\n")
        _stage_all(repo_b)  # fully covered -- 100.0% coverage

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        run_codeowners_health([repo_a, repo_b], out_dir)

        summary = json.loads((out_dir / "codeowners_health_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["repos_with_codeowners"] == 1
        assert summary["repos_without_codeowners"] == 1
        assert summary["average_coverage_pct"] == 50.0
