from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from _doc_quality_helpers import HAS_INTERROGATE, commit, init_repo

from repo_analyser.collectors.doc_quality import run_doc_quality


class TestRunDocQuality:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_doc_quality([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_writes_one_row_per_repo_with_repo_column(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        init_repo(repo_a)
        commit(repo_a, "a.py", '"""Doc."""\n', date="2026-01-01T00:00:00")
        repo_b = tmp_path / "repo-b"
        init_repo(repo_b)
        commit(repo_b, "main.go", "package main\n", date="2026-01-01T00:00:00")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_doc_quality([repo_a, repo_b], out_dir)
        rows = {r["repo"]: r for r in csv.DictReader(open(out_path))}
        assert rows["repo-a"]["doc_comment_tool"] == "interrogate"
        assert rows["repo-b"]["skip_reason"] == (
            "no keyless scriptable doc-coverage-percentage tool for this language yet"
        )

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_writes_summary_json_with_real_counts_and_does_not_blend_signals(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        init_repo(repo_a)
        commit(repo_a, "a.py", '"""Doc."""\n\n\ndef f():\n    return 1\n', date="2026-01-01T00:00:00")
        repo_b = tmp_path / "repo-b"
        init_repo(repo_b)
        (repo_b / "package.json").write_text(json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^1.0.0"}}))
        (repo_b / ".eslintrc.json").write_text(json.dumps({"extends": ["plugin:jsdoc/recommended"]}))
        commit(repo_b, "index.js", "1;\n", date="2026-01-01T00:00:00")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_doc_quality([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "doc_quality_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["repos_with_measured_python_doc_coverage"] == 1
        # a real interrogate measurement only, never diluted by JS's
        # presence-only 0.0 sentinel.
        assert summary["mean_python_doc_comment_coverage_pct"] == 50.0
        assert summary["repos_with_eslint_jsdoc_signal"] == 1

    def test_summary_mean_is_none_when_no_repo_has_a_real_measurement(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_repo(repo)
        commit(repo, "main.go", "package main\n", date="2026-01-01T00:00:00")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_doc_quality([repo], out_dir)
        summary = json.loads((out_dir / "doc_quality_summary.json").read_text())
        assert summary["mean_python_doc_comment_coverage_pct"] is None
