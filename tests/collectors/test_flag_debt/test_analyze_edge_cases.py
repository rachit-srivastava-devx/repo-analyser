from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.flag_debt import analyze_repo

from ._flag_debt_helpers import _git_repo


class TestAnalyzeRepoDuplicateDefinitions:
    def test_same_flag_defined_in_two_places_counts_as_one_duplicate(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "flags.json").write_text(json.dumps({"shared": True}))
        (repo / "config.py").write_text('FEATURE_FLAGS = {\n    "shared": True,\n}\n')
        result = analyze_repo(repo)
        assert result.flags_defined_count == 1
        assert result.duplicate_definition_count == 1


class TestAnalyzeRepoMalformedConfig:
    def test_malformed_flags_json_does_not_crash_whole_repo_analysis(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "flags.json").write_text("{not valid json")
        (repo / "app.py").write_text('is_enabled("still_works")\n')
        result = analyze_repo(repo)
        assert result.flags_defined_count == 0
        assert result.flags_referenced_count == 1
        assert result.undefined_flag_references == "still_works"
