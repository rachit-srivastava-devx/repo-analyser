from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codebase_modularity.module_size import find_module_size_findings

from ._codebase_modularity_helpers import init_repo, make_source_file, write


def test_file_at_exactly_500_loc_is_not_oversized(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    make_source_file(repo, "big.py", 500)
    result = find_module_size_findings(repo)
    assert result.oversized_file_count == 0
    assert result.oversized_files == ""


def test_file_at_501_loc_is_oversized(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    make_source_file(repo, "big.py", 501)
    result = find_module_size_findings(repo)
    assert result.oversized_file_count == 1
    assert "big.py(501)" in result.oversized_files


def test_directory_with_exactly_40_files_is_not_oversized(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(40):
        write(repo, f"pkg/f{i}.py", "x = 1\n")
    result = find_module_size_findings(repo)
    assert result.oversized_package_count == 0
    assert result.oversized_packages == ""


def test_directory_with_41_files_is_oversized(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(41):
        write(repo, f"pkg/f{i}.py", "x = 1\n")
    result = find_module_size_findings(repo)
    assert result.oversized_package_count == 1
    assert "pkg(41)" in result.oversized_packages


def test_files_in_subdirectory_do_not_count_toward_parent_directory(tmp_path: Path) -> None:
    """Non-recursive: 41 files spread across pkg/ (1 file) and pkg/sub/ (40
    files) must NOT trip pkg's own oversized-package count -- each
    directory's count is its own direct files only."""
    repo = init_repo(tmp_path / "r")
    write(repo, "pkg/only_direct_file.py", "x = 1\n")
    for i in range(40):
        write(repo, f"pkg/sub/f{i}.py", "x = 1\n")
    result = find_module_size_findings(repo)
    assert result.oversized_package_count == 0


def test_empty_repo_has_zero_counts_not_an_error(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    result = find_module_size_findings(repo)
    assert result.oversized_file_count == 0
    assert result.oversized_package_count == 0


def test_non_source_extensions_are_not_counted_toward_package_size(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(50):
        write(repo, f"assets/img{i}.png", "not-really-an-image")
    result = find_module_size_findings(repo)
    assert result.oversized_package_count == 0


def test_excluded_dirs_are_skipped(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(50):
        write(repo, f"node_modules/dep/f{i}.js", "module.exports = {};\n")
    result = find_module_size_findings(repo)
    assert result.oversized_file_count == 0
    assert result.oversized_package_count == 0


def test_sample_is_capped_and_count_reports_true_total(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(15):
        make_source_file(repo, f"big{i}.py", 501)
    result = find_module_size_findings(repo)
    assert result.oversized_file_count == 15
    assert result.oversized_files.count("(501)") == 10  # capped at 10 shown entries
    assert "+5 more" in result.oversized_files
