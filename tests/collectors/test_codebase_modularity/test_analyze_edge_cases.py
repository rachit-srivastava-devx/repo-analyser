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


def test_repo_directory_named_like_an_excluded_dir_part_is_still_scanned(tmp_path: Path) -> None:
    """discovery.py must exclude EXCLUDE_DIR_PARTS relative to the repo
    root, not against the file's full absolute path -- otherwise a repo
    whose own directory name happens to equal an excluded part (e.g. a
    checkout literally named "build", "dist", "vendor", or "target", all
    plausible real repo names) has every one of its files silently
    skipped, indistinguishable from "genuinely found nothing".

    Only asserts on oversized_file_count (module_size.py's iter_source_files
    path, the thing this test targets) -- not on god_class_count/
    god_class_language_supported, which additionally gate on
    core.lang.detect_repo_language. That function has the identical
    absolute-path-vs-relative-path bug independently (core/lang.py:99), so
    it would still misreport "unknown" for a repo named "build" even after
    this package's own discovery.py fix; that's pre-existing shared
    infrastructure this branch does not touch or claim to fix."""
    repo = init_repo(tmp_path / "build")
    write(repo, "huge.py", "\n".join(f"x{i} = {i}" for i in range(600)) + "\n")
    commit_all(repo, "init")

    result = analyze_repo(repo)
    assert result.oversized_file_count == 1


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
