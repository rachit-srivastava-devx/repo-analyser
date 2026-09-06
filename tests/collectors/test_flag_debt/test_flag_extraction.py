from __future__ import annotations

from repo_analyser.collectors.flag_debt.flag_extraction import (
    extract_dict_literal_definitions,
    extract_flag_references,
)


class TestExtractFlagReferences:
    def test_is_enabled_string_literal(self) -> None:
        assert extract_flag_references('if is_enabled("new_checkout"):') == {"new_checkout"}

    def test_feature_enabled_string_literal(self) -> None:
        assert extract_flag_references("feature_enabled('beta_ui')") == {"beta_ui"}

    def test_is_feature_enabled_camel_case(self) -> None:
        text = 'if (isFeatureEnabled("dark_mode")) { render(); }'
        assert extract_flag_references(text) == {"dark_mode"}

    def test_non_literal_first_arg_is_skipped_silently(self) -> None:
        assert extract_flag_references("is_enabled(flag_name_variable)") == set()

    def test_case_sensitive_names_do_not_fuzzy_match(self) -> None:
        assert extract_flag_references('Is_Enabled("nope")') == set()
        assert extract_flag_references('IS_ENABLED("nope")') == set()

    def test_no_calls_anywhere_is_a_normal_empty_result(self) -> None:
        assert extract_flag_references("def f():\n    return 1\n") == set()

    def test_multiple_distinct_calls(self) -> None:
        text = 'is_enabled("a")\nfeature_enabled("b")\n'
        assert extract_flag_references(text) == {"a", "b"}


class TestExtractDictLiteralDefinitions:
    def test_python_feature_flags_dict(self) -> None:
        text = 'FEATURE_FLAGS = {\n    "new_checkout": True,\n    "beta_ui": False,\n}\n'
        assert extract_dict_literal_definitions(text) == ["new_checkout", "beta_ui"]

    def test_js_const_flags_object(self) -> None:
        text = 'const flags = {\n  "darkMode": true,\n};\n'
        assert extract_dict_literal_definitions(text) == ["darkMode"]

    def test_exported_js_flags_object(self) -> None:
        text = 'export const flags = {\n  "betaUi": true,\n};\n'
        assert extract_dict_literal_definitions(text) == ["betaUi"]

    def test_nested_metadata_excludes_inner_keys(self) -> None:
        text = 'FEATURE_FLAGS = {\n    "beta": {"enabled": True, "owner": "x"},\n}\n'
        assert extract_dict_literal_definitions(text) == ["beta"]

    def test_empty_dict_yields_no_keys(self) -> None:
        assert extract_dict_literal_definitions("FEATURE_FLAGS = {}\n") == []

    def test_no_dict_literal_returns_empty_list(self) -> None:
        assert extract_dict_literal_definitions("x = 1\n") == []

    def test_truncated_dict_does_not_raise(self) -> None:
        text = 'FEATURE_FLAGS = {\n    "new_checkout": True,\n'
        assert extract_dict_literal_definitions(text) == ["new_checkout"]
