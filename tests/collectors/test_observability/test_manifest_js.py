from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.observability.manifest_js import js_dependency_names, read_package_json


class TestReadPackageJson:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        assert read_package_json(tmp_path) == {}

    def test_malformed_json_returns_empty_dict_not_raise(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not valid json,,,")
        assert read_package_json(tmp_path) == {}

    def test_valid_json_parses(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"winston": "^3.0.0"}}))
        assert read_package_json(tmp_path) == {"dependencies": {"winston": "^3.0.0"}}


class TestJsDependencyNames:
    def test_merges_dependencies_and_dev_dependencies(self) -> None:
        pkg = {"dependencies": {"winston": "^3.0.0"}, "devDependencies": {"jest": "^29.0.0"}}
        assert js_dependency_names(pkg) == {"winston", "jest"}

    def test_non_dict_dependencies_key_degrades_to_empty_not_raise(self) -> None:
        # malformed-but-valid-JSON: "dependencies" is a list, not an
        # object -- must degrade gracefully, not raise.
        assert js_dependency_names({"dependencies": ["winston"]}) == set()

    def test_missing_keys_return_empty_set(self) -> None:
        assert js_dependency_names({}) == set()
