from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from _dead_code_helpers import write_files

from repo_analyser.collectors.dead_code.runner import run_dead_code


class TestRunDeadCode:
    def test_writes_summary_csv_findings_csv_and_json_for_mixed_repos(self, tmp_path: Path) -> None:
        py_repo = write_files(tmp_path / "py_repo", {"a.py": "x = 1\n"})
        js_repo = write_files(tmp_path / "js_repo", {
            "used.js": "export const usedThing = 1;\n",
            "unused.js": "export const unusedThing = 2;\n",
            "consumer.js": "import { usedThing } from './used.js';\nconsole.log(usedThing);\n",
        })
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        out_path = run_dead_code([py_repo, js_repo], out_dir)
        assert out_path == out_dir / "dead_code.csv"
        assert out_path.exists()

        # Python-specific counts depend on whether vulture is installed on
        # this machine (see test_analyze.py's skipif-guarded real-vulture
        # tests for that) -- this test only asserts what's true regardless
        # of environment: both repos are present, and the JS side (which
        # needs no external tool) is exactly right.
        csv_text = out_path.read_text()
        assert "py_repo" in csv_text
        assert "js_repo" in csv_text

        # exact-name comparison via csv.DictReader, not a raw substring
        # check -- "usedThing" is itself a substring of "unusedThing".
        with open(out_dir / "dead_code_findings.csv", newline="") as f:
            finding_names = {row["name"] for row in csv.DictReader(f)}
        assert "unusedThing" in finding_names
        assert "usedThing" not in finding_names

        summary = json.loads((out_dir / "dead_code_summary.json").read_text())
        assert summary["repos_total"] == 2
        assert summary["repos_with_js_checked"] == 1  # only js_repo has JS files
        assert summary["total_js_unreferenced_exports"] == 1

    def test_empty_repo_list_produces_valid_headers_only_output(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_dead_code([], out_dir)
        summary = json.loads((out_dir / "dead_code_summary.json").read_text())
        assert summary["repos_total"] == 0
        assert summary["total_python_dead_code_items"] == 0
        assert summary["total_js_unreferenced_exports"] == 0

    def test_summary_reports_zero_python_checked_when_vulture_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Deterministic regardless of the real machine's vulture status --
        # forces the "tool unavailable" branch to verify the summary JSON's
        # aggregation (sum over zero checked repos) doesn't crash either.
        monkeypatch.setattr(
            "repo_analyser.collectors.dead_code.analyze.vulture_available", lambda: False
        )
        py_repo = write_files(tmp_path / "py_repo", {"a.py": "x = 1\n"})
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_dead_code([py_repo], out_dir)
        summary = json.loads((out_dir / "dead_code_summary.json").read_text())
        assert summary["repos_with_python_checked"] == 0
        assert summary["total_python_dead_code_items"] == 0
        assert summary["repos_with_tool_unavailable"] == {"py_repo": ["vulture"]}
