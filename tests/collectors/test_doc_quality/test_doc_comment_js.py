from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.doc_quality.doc_comment_js import (
    _js_doc_comment_signal,
    _read_package_json,
)


class TestReadPackageJson:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        assert _read_package_json(tmp_path) == {}

    def test_malformed_json_returns_empty_dict(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not valid json,,,")
        assert _read_package_json(tmp_path) == {}

    def test_valid_json_is_parsed(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^48.0.0"}}))
        assert _read_package_json(tmp_path)["devDependencies"] == {"eslint-plugin-jsdoc": "^48.0.0"}


class TestJsDocCommentSignal:
    def test_dep_and_config_both_present_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^48.0.0"}}))
        (tmp_path / ".eslintrc.json").write_text(
            json.dumps({"plugins": ["jsdoc"], "extends": ["plugin:jsdoc/recommended"]}))
        pct, tool, skip_reason = _js_doc_comment_signal(tmp_path)
        assert tool == "eslint-plugin-jsdoc"
        assert skip_reason == ""
        assert pct == 0.0  # presence-only signal, never a real percentage

    def test_dep_present_without_config_reference_names_the_gap(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^48.0.0"}}))
        (tmp_path / ".eslintrc.json").write_text(json.dumps({"extends": ["eslint:recommended"]}))
        pct, tool, skip_reason = _js_doc_comment_signal(tmp_path)
        assert tool == ""
        assert "devDependency" in skip_reason and "no eslint config file references" in skip_reason

    def test_config_reference_without_dep_names_the_gap(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {}}))
        (tmp_path / ".eslintrc.json").write_text(json.dumps({"extends": ["plugin:jsdoc/recommended"]}))
        pct, tool, skip_reason = _js_doc_comment_signal(tmp_path)
        assert tool == ""
        assert "not a package.json devDependency" in skip_reason

    def test_neither_present_names_the_gap(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"lodash": "^4.0.0"}}))
        pct, tool, skip_reason = _js_doc_comment_signal(tmp_path)
        assert tool == ""
        assert "no eslint-plugin-jsdoc devDependency or jsdoc-referencing eslint config found" == skip_reason

    def test_jsdoc_substring_in_unrelated_word_does_not_false_positive(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"devDependencies": {"eslint-plugin-jsdoc": "^48.0.0"}}))
        (tmp_path / ".eslintrc.json").write_text(json.dumps({"extends": ["some-other-unrelated-thing"]}))
        _, tool, _ = _js_doc_comment_signal(tmp_path)
        assert tool == ""
