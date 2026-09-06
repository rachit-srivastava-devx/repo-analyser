from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.flag_debt.flag_definitions import collect_defined_flags


class TestRootConfigFiles:
    def test_flags_json_top_level_keys(self, tmp_path: Path) -> None:
        (tmp_path / "flags.json").write_text(json.dumps({"a": True, "b": False}))
        assert sorted(collect_defined_flags(tmp_path, [])) == ["a", "b"]

    def test_flags_yaml_top_level_keys(self, tmp_path: Path) -> None:
        (tmp_path / "flags.yaml").write_text("a: true\nb: false\n")
        assert sorted(collect_defined_flags(tmp_path, [])) == ["a", "b"]

    def test_dot_flagsmith_json_parsed_as_json(self, tmp_path: Path) -> None:
        (tmp_path / ".flagsmith.json").write_text(json.dumps({"c": True}))
        assert collect_defined_flags(tmp_path, []) == ["c"]

    def test_nested_yaml_collects_only_top_level_keys(self, tmp_path: Path) -> None:
        (tmp_path / "flags.yaml").write_text("beta:\n  enabled: true\n  owner: x\n")
        assert collect_defined_flags(tmp_path, []) == ["beta"]

    def test_malformed_json_is_zero_definitions_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "flags.json").write_text("{not valid json")
        assert collect_defined_flags(tmp_path, []) == []

    def test_malformed_yaml_is_zero_definitions_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "flags.yaml").write_text("a: [1, 2\n")
        assert collect_defined_flags(tmp_path, []) == []

    def test_missing_files_return_empty(self, tmp_path: Path) -> None:
        assert collect_defined_flags(tmp_path, []) == []

    def test_non_mapping_json_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "flags.json").write_text(json.dumps(["a", "b"]))
        assert collect_defined_flags(tmp_path, []) == []


class TestSourceTextDictLiterals:
    def test_collects_from_source_texts_too(self, tmp_path: Path) -> None:
        text = 'FEATURE_FLAGS = {\n    "d": True,\n}\n'
        assert collect_defined_flags(tmp_path, [text]) == ["d"]

    def test_combines_root_config_and_source_dicts(self, tmp_path: Path) -> None:
        (tmp_path / "flags.json").write_text(json.dumps({"a": True}))
        text = 'FEATURE_FLAGS = {\n    "b": True,\n}\n'
        assert sorted(collect_defined_flags(tmp_path, [text])) == ["a", "b"]
