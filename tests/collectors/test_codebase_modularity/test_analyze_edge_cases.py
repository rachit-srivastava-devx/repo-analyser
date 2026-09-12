from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codebase_modularity.analyze import analyze_repo

from ._codebase_modularity_helpers import (
    class_with_method_count,
    commit_all,
    init_repo,
    write,
)


def test_nonexistent_path_reports_skip_reason(tmp_path: Path) -> None:
    result = analyze_repo(tmp_path / "does_not_exist")
    assert result.skip_reason != ""
    assert result.oversized_file_count == 0
    assert result.god_class_language_supported is False


def test_directory_that_is_not_a_git_repo_reports_skip_reason(tmp_path: Path) -> None:
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    write(plain_dir, "a.py", "x = 1\n")
    result = analyze_repo(plain_dir)
    assert "not a git repository" in result.skip_reason


def test_bare_git_dir_with_nothing_else_is_not_an_error(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    result = analyze_repo(repo)
    assert result.skip_reason == ""
    assert result.oversized_file_count == 0
    assert result.oversized_package_count == 0
    assert result.god_class_count == 0


def test_real_repo_with_findings_across_all_three_signals(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "big.py", "\n".join(f"x{i} = {i}" for i in range(600)) + "\n")
    write(repo, "godclass.py", class_with_method_count("Big", 25))
    write(repo, ".importlinter", "[importlinter]\nroot_package = app\n")
    commit_all(repo, "init")

    result = analyze_repo(repo)
    assert result.skip_reason == ""
    assert result.oversized_file_count >= 1
    assert result.god_class_count == 1
    assert result.god_class_language_supported is True
    assert result.layering_tool_detected == "import-linter"
