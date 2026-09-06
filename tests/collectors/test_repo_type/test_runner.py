from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.repo_type import run_repo_type

from ._repo_type_helpers import _git_repo


class TestRunRepoType:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_repo_type([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_expected_columns(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "nx.json").write_text("{}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_repo_type([repo], out_dir)
        rows = list(csv.DictReader(open(out_path)))
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "repo", "primary_type", "content_types", "signals_matched", "detection_notes",
        }
        assert rows[0]["primary_type"] == "monorepo"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = _git_repo(tmp_path / "repo-a")
        repo_b = _git_repo(tmp_path / "repo-b")
        (repo_b / "nx.json").write_text("{}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_repo_type([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "repo_type_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["primary_type_counts"]["single_repo"] == 1
        assert summary["primary_type_counts"]["monorepo"] == 1
