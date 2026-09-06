from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.license_compliance import analyze_repo
from repo_analyser.collectors.license_compliance.detect_license_file import (
    find_license_file,
    read_license_text,
)

from ._license_compliance_helpers import MIT_TEXT, _git_repo


class TestFindLicenseFile:
    def test_missing_entirely_returns_none(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        assert find_license_file(repo) is None

    def test_plain_license_file_is_found(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text(MIT_TEXT)
        assert find_license_file(repo) == repo / "LICENSE"

    def test_case_insensitive_filename_match(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "license").write_text(MIT_TEXT)
        found = find_license_file(repo)
        assert found is not None and found.name == "license"

    def test_precedence_prefers_license_over_license_md(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE.md").write_text(MIT_TEXT)
        (repo / "LICENSE").write_text(MIT_TEXT)
        found = find_license_file(repo)
        assert found is not None and found.name == "LICENSE"

    def test_precedence_falls_back_to_copying_when_only_that_exists(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "COPYING").write_text(MIT_TEXT)
        found = find_license_file(repo)
        assert found is not None and found.name == "COPYING"

    def test_multiple_license_like_files_present_picks_precedence_winner(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "COPYING").write_text(MIT_TEXT)
        (repo / "LICENSE.txt").write_text(MIT_TEXT)
        (repo / "LICENSE.md").write_text(MIT_TEXT)
        found = find_license_file(repo)
        assert found is not None and found.name == "LICENSE.md"

    def test_license_directory_is_not_treated_as_a_file(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").mkdir()
        assert find_license_file(repo) is None


class TestReadLicenseText:
    def test_empty_license_file_yields_empty_text_and_unknown_id(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "LICENSE").write_text("")
        assert read_license_text(repo / "LICENSE") == ""
        result = analyze_repo(repo)
        assert result.license_id == "unknown"
        assert result.license_file == "LICENSE"

    def test_unreadable_path_does_not_crash(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        assert read_license_text(repo / "no-such-file") == ""
