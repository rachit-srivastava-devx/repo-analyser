from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.reporting.report import _table, render_report


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class TestTable:
    def test_empty_rows_returns_no_data_marker(self) -> None:
        assert _table([], ["a", "b"]) == "_(no data)_\n"

    def test_real_rows_render_as_github_markdown_table(self) -> None:
        out = _table([{"repo": "a", "score": 1}, {"repo": "b", "score": 2}], ["repo", "score"])
        assert "| repo" in out
        assert "| a" in out and "| b" in out
        assert "---" in out

    def test_pipe_character_in_a_cell_is_escaped_not_corrupting_the_table(self) -> None:
        # a commit subject, semgrep message, or file path can contain a
        # literal "|" -- unescaped, it would silently break the table's
        # column structure when the markdown is rendered.
        out = _table([{"subject": "fix: a | b conflict"}], ["subject"])
        assert "a \\| b" in out
        # exactly the header + separator + one data row -- not corrupted
        # into extra columns/rows by the embedded pipe.
        assert len(out.strip().splitlines()) == 3

    def test_limit_truncates_rows(self) -> None:
        rows = [{"n": str(i)} for i in range(10)]
        out = _table(rows, ["n"], limit=3)
        lines = out.strip().splitlines()
        assert len(lines) == 2 + 3  # header + separator + 3 data rows

    def test_missing_column_defaults_to_empty_string_not_crash(self) -> None:
        out = _table([{"a": "1"}], ["a", "b"])
        assert "| a" in out or "|---" in out  # renders without KeyError


class TestRenderReport:
    def test_empty_out_dir_produces_a_minimal_valid_report(self, tmp_path: Path) -> None:
        report_path = render_report(tmp_path, "myrepo")
        assert report_path.exists()
        assert report_path.read_text().startswith("# Repo Analyser report: myrepo")

    def test_test_quality_section_reads_the_real_summary_key(self, tmp_path: Path) -> None:
        # regression test for a real bug: this section read
        # `repos_with_test_failures`, a key testquality.py never writes
        # (the real key is `repos_with_real_test_failures_right_now`) --
        # silently always rendering "0 repos have failing tests" no
        # matter what the actual data said.
        _write_json(tmp_path / "testquality_summary.json", {
            "total_repos": 5, "repos_with_unit_script": 5,
            "repos_with_real_test_failures_right_now": 3,
        })
        report_path = render_report(tmp_path, "myrepo")
        text = report_path.read_text()
        assert "3 repos have failing tests RIGHT NOW" in text

    def test_inventory_section_included_when_data_present(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "inventory.csv", [
            {"repo": "a", "tier": "active", "total_commits": "10", "unique_authors": "2",
             "bus_factor_gini": "0.1", "top_author_share": "0.6"},
        ])
        text = render_report(tmp_path, "myrepo").read_text()
        assert "## Repo activity" in text
        assert "| a" in text

    def test_sections_with_no_data_are_omitted_not_shown_empty(self, tmp_path: Path) -> None:
        text = render_report(tmp_path, "myrepo").read_text()
        assert "## Repo activity" not in text
        assert "## Security" not in text

    def test_run_log_summarizes_module_outcomes(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "run_log.json", {
            "repo_count": 3,
            "modules_run": [
                {"module": "inventory", "status": "ok"},
                {"module": "churn", "status": "error"},
            ],
        })
        text = render_report(tmp_path, "myrepo").read_text()
        assert "Repos analyzed: 3" in text
        assert "Modules completed: 1/2" in text
        assert "churn" in text
