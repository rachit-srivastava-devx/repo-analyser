from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.code_quality import (
    _mi_grade,
    _python_files,
    analyze_repo,
    run_code_quality,
)


class TestMiGrade:
    def test_high_score_is_a(self) -> None:
        assert _mi_grade(85.0) == "A"

    def test_boundary_twenty_is_a(self) -> None:
        assert _mi_grade(20.0) == "A"

    def test_mid_score_is_b(self) -> None:
        assert _mi_grade(15.0) == "B"

    def test_boundary_ten_is_b(self) -> None:
        assert _mi_grade(10.0) == "B"

    def test_low_score_is_c(self) -> None:
        assert _mi_grade(5.0) == "C"


class TestPythonFiles:
    def test_finds_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        assert len(_python_files(tmp_path)) == 2

    def test_excludes_venv_and_pycache(self, tmp_path: Path) -> None:
        (tmp_path / "real.py").write_text("x = 1\n")
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "vendored.py").write_text("y = 2\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("z = 3\n")
        files = _python_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "real.py"


class TestAnalyzeRepo:
    def test_non_python_repo_is_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "main.go").write_text("package main\n")
        result = analyze_repo(tmp_path)
        assert result.ran is False
        assert "not supported" in result.skip_reason

    def test_empty_repo_is_skipped_as_unsupported_language_not_a_crash(self, tmp_path: Path) -> None:
        # an empty repo has no dominant extension at all (detect_repo_language
        # returns "unknown"), so it's caught by the language check -- there is
        # no separate "python but zero files" state to hit (see analyze_repo's
        # own comment on why that branch doesn't exist).
        result = analyze_repo(tmp_path)
        assert result.ran is False
        assert "not supported" in result.skip_reason

    def test_real_valid_python_file_gets_scored(self, tmp_path: Path) -> None:
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        result = analyze_repo(tmp_path)
        assert result.ran is True
        assert result.files_analyzed == 1
        assert result.mean_maintainability_index == 88.6  # radon's real, observed output for this snippet
        assert result.grade == "A"

    def test_syntax_error_file_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text("def f(:\n    this is not valid python\n")
        (tmp_path / "valid.py").write_text("def add(a, b):\n    return a + b\n")
        result = analyze_repo(tmp_path)
        assert result.ran is True
        assert result.files_analyzed == 1
        assert result.files_skipped == 1

    def test_all_files_broken_reports_named_skip_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text("def f(:\n    invalid\n")
        result = analyze_repo(tmp_path)
        assert result.ran is False
        assert "no file produced a valid MI score" in result.skip_reason

    def test_lowest_file_identifies_the_worst_scorer(self, tmp_path: Path) -> None:
        (tmp_path / "simple.py").write_text("x = 1\n")
        result = analyze_repo(tmp_path)
        assert result.lowest_file == "simple.py"
        assert result.lowest_file_mi == result.mean_maintainability_index


class TestRunCodeQuality:
    def test_summary_counts_and_grade_distribution(self, tmp_path: Path) -> None:
        py_repo = tmp_path / "py-repo"
        py_repo.mkdir()
        (py_repo / "a.py").write_text("def add(a, b):\n    return a + b\n")

        go_repo = tmp_path / "go-repo"
        go_repo.mkdir()
        (go_repo / "main.go").write_text("package main\n")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_code_quality([py_repo, go_repo], out_dir)

        summary = json.loads((out_dir / "code_quality_summary.json").read_text())
        assert summary["repos_analyzed"] == 1
        assert summary["repos_skipped"] == 1
        assert summary["mean_maintainability_index"] == 88.6  # radon's real, observed output for this snippet
        assert summary["grade_distribution"]["A"] == 1
