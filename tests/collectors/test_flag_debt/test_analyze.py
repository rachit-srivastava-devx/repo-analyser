from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.flag_debt import analyze_repo

from ._flag_debt_helpers import _git_repo


class TestAnalyzeRepoZeroFlags:
    def test_no_flags_anywhere_is_all_zero_not_a_failure(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "main.py").write_text("def main():\n    return 1\n")
        result = analyze_repo(repo)
        assert result.flags_referenced_count == 0
        assert result.flags_defined_count == 0
        assert result.orphaned_flag_definitions == ""
        assert result.undefined_flag_references == ""
        assert result.sdk_detected == ""
        assert result.duplicate_definition_count == 0


class TestAnalyzeRepoSdkDetection:
    def test_sdk_import_detected(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "app.py").write_text("import ldclient\n")
        result = analyze_repo(repo)
        assert result.sdk_detected == "launchdarkly"


class TestAnalyzeRepoOrphanedAndUndefined:
    def test_orphaned_definition_defined_but_never_referenced(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "flags.json").write_text(json.dumps({"dead_flag": True}))
        result = analyze_repo(repo)
        assert result.flags_defined_count == 1
        assert result.orphaned_flag_definitions == "dead_flag"
        assert result.flags_referenced_count == 0

    def test_undefined_reference_referenced_but_never_defined(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "app.py").write_text('is_enabled("remote_only_flag")\n')
        result = analyze_repo(repo)
        assert result.flags_referenced_count == 1
        assert result.undefined_flag_references == "remote_only_flag"
        assert result.flags_defined_count == 0

    def test_referenced_and_defined_flag_is_neither_orphaned_nor_undefined(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "flags.json").write_text(json.dumps({"shared_flag": True}))
        (repo / "app.py").write_text('is_enabled("shared_flag")\n')
        result = analyze_repo(repo)
        assert result.orphaned_flag_definitions == ""
        assert result.undefined_flag_references == ""


class TestAnalyzeRepoNonLiteralArgSkipped:
    def test_variable_first_arg_is_skipped_not_crashed(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "app.py").write_text("is_enabled(flag_variable)\n")
        result = analyze_repo(repo)
        assert result.flags_referenced_count == 0
