from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from repo_analyser.collectors.lint_quality import (
    _eslint,
    _ruff,
    _staticcheck,
    analyze_repo,
    run_lint_quality,
)


class TestEslintSkipPaths:
    def test_no_node_modules_binary_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _eslint(repo)
        assert result.ran is False
        assert "not in node_modules" in result.skip_reason

    def test_binary_present_but_no_config_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "node_modules" / ".bin").mkdir(parents=True)
        (repo / "node_modules" / ".bin" / "eslint").write_text("#!/bin/sh\necho '[]'\n")
        (repo / "node_modules" / ".bin" / "eslint").chmod(0o755)
        result = _eslint(repo)
        assert result.ran is False
        assert "no eslint config" in result.skip_reason


class TestRuffRealExecution:
    def test_clean_file_reports_zero_errors(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "clean.py").write_text("def f():\n    return 1\n")
        result = _ruff(repo)
        assert result.ran is True
        assert result.error_count == 0

    def test_real_violation_is_detected_and_counted(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "bad.py").write_text("import os\nimport sys\n\ndef f():\n    return 1\n")
        result = _ruff(repo)
        assert result.ran is True
        assert result.error_count >= 2  # both unused imports (F401)
        assert "F401" in result.top_rules


class TestStaticcheckSkipPaths:
    def test_no_go_mod_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _staticcheck(repo)
        assert result.ran is False


class TestAnalyzeRepoDispatch:
    def test_python_dispatches_to_ruff(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("x = 1\n")
        result = analyze_repo(repo)
        assert result.linter == "ruff"

    def test_go_dispatches_to_staticcheck(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.go").write_text("package main\n")
        result = analyze_repo(repo)
        assert result.linter == "staticcheck"

    def test_javascript_dispatches_to_eslint(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.ts").write_text("const x = 1;\n")
        result = analyze_repo(repo)
        assert result.linter == "eslint"

    def test_unsupported_language_names_itself_in_skip_reason(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Main.java").write_text("")
        result = analyze_repo(repo)
        assert result.linter == "none"
        assert "java" in result.skip_reason


class TestRunLintQuality:
    def test_summary_totals_only_count_repos_that_actually_ran(self, tmp_path: Path) -> None:
        clean_repo = tmp_path / "clean"
        clean_repo.mkdir()
        (clean_repo / "ok.py").write_text("def f():\n    return 1\n")
        unsupported_repo = tmp_path / "unsupported"
        unsupported_repo.mkdir()
        (unsupported_repo / "Main.java").write_text("")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_lint_quality([clean_repo, unsupported_repo], out_dir)
        summary = json.loads((out_dir / "lint_quality_summary.json").read_text())
        assert summary["repos_linted"] == 1
        assert summary["repos_skipped"] == 1
        assert "unsupported" in summary["skip_reasons"]


class TestSuppressionDensity:
    """docs/ROADMAP.md's lint_quality.py extension: `# noqa` / `# type:
    ignore` (Python), `eslint-disable` (JS/TS), `//nolint` (Go), counted
    per-language and normalized per that language's own KLOC."""

    def test_python_noqa_comments_increase_density(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text(
            "import os  # noqa\nimport sys  # noqa\ndef f():\n    return 1\n"
        )
        result = analyze_repo(repo)
        assert result.python_suppression_count == 2
        assert result.python_kloc > 0
        assert result.python_suppression_density > 0

    def test_python_type_ignore_is_also_counted(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("x: int = foo()  # type: ignore\n")
        result = analyze_repo(repo)
        assert result.python_suppression_count == 1
        assert result.python_suppression_density > 0

    def test_javascript_eslint_disable_line_and_block_comments_are_both_counted(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.ts").write_text(
            "// eslint-disable-next-line no-unused-vars\n"
            "const x = 1;\n"
            "/* eslint-disable no-console */\n"
            "console.log(x);\n"
        )
        result = analyze_repo(repo)
        assert result.javascript_suppression_count == 2
        assert result.javascript_suppression_density > 0

    def test_go_nolint_is_counted(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.go").write_text("package main\n\nfunc f() { //nolint\n}\n")
        result = analyze_repo(repo)
        assert result.go_suppression_count == 1
        assert result.go_suppression_density > 0

    def test_zero_suppressions_is_a_real_zero_not_an_error(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "clean.py").write_text("def f():\n    return 1\n")
        result = analyze_repo(repo)
        assert result.python_suppression_count == 0
        assert result.python_suppression_density == 0.0
        # the underlying linter dispatch/skip logic is untouched by this addition
        assert result.ran is True

    def test_no_files_of_a_language_gives_zero_kloc_not_a_crash(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "only.py").write_text("x = 1\n")
        result = analyze_repo(repo)
        assert result.go_kloc == 0.0
        assert result.go_suppression_density == 0.0
        assert result.javascript_kloc == 0.0
        assert result.javascript_suppression_density == 0.0

    def test_polyglot_repo_normalizes_per_language_kloc_not_total_repo_kloc(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        # A small Python file with 2 noqa comments in 4 lines: KLOC = 4/1000,
        # density = 2 / (4/1000) = 500.0.
        (repo / "a.py").write_text(
            "import os  # noqa\nimport sys  # noqa\ndef f():\n    return 1\n"
        )
        # A much larger, suppression-free JS file (996 lines): if the
        # implementation mistakenly divided by *total repo* KLOC instead of
        # python's own KLOC, repo-wide lines would be 996 + 4 = 1000 and the
        # python density would come out as 2 / (1000/1000) == 2.0 instead of
        # the correct 500.0 -- a large, unmistakable gap, not a rounding
        # difference, so this assertion actually pins the bug down.
        (repo / "b.js").write_text("\n".join(f"const x{i} = {i};" for i in range(996)) + "\n")

        result = analyze_repo(repo)
        assert result.python_suppression_count == 2
        assert result.python_kloc == pytest.approx(0.004)
        assert result.python_suppression_density == pytest.approx(500.0)
        # the JS file itself has zero suppressions -- confirms its density
        # isn't somehow inflated by the python file's noqa comments either.
        assert result.javascript_suppression_count == 0
        assert result.javascript_kloc == pytest.approx(0.996)
        assert result.javascript_suppression_density == 0.0

    def test_suppression_columns_land_in_csv_alongside_existing_columns(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("import os  # noqa\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_lint_quality([repo], out_dir)
        with open(out_dir / "lint_quality.csv", newline="") as f:
            row = next(csv.DictReader(f))
        for col in ("repo", "linter", "ran", "error_count", "warning_count",
                    "files_with_issues", "top_rules", "skip_reason"):
            assert col in row, f"pre-existing column {col!r} missing from lint_quality.csv"
        for col in ("python_suppression_count", "python_kloc", "python_suppression_density",
                    "javascript_suppression_count", "javascript_kloc", "javascript_suppression_density",
                    "go_suppression_count", "go_kloc", "go_suppression_density"):
            assert col in row, f"new column {col!r} missing from lint_quality.csv"
        assert row["python_suppression_count"] == "1"
