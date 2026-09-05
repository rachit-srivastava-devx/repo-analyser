from __future__ import annotations

import json
from pathlib import Path

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
