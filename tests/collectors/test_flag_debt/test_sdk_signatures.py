from __future__ import annotations

from repo_analyser.collectors.flag_debt.sdk_signatures import find_sdk_import


class TestFindSdkImportPython:
    def test_launchdarkly_bare_import(self) -> None:
        assert find_sdk_import("import ldclient") == "launchdarkly"

    def test_launchdarkly_from_import(self) -> None:
        assert find_sdk_import("from launchdarkly.client import LDClient") == "launchdarkly"

    def test_splitio_from_import(self) -> None:
        assert find_sdk_import("from splitio import get_factory") == "split.io"

    def test_ordinary_import_returns_none(self) -> None:
        assert find_sdk_import("import os.path") is None


class TestFindSdkImportJavaScript:
    def test_named_import_captures_path_not_local_binding(self) -> None:
        # Regression guard: the local binding name "LDClient" must never be
        # what gets matched against the SDK token list -- only the actual
        # package path string after "from" should be.
        line = 'import LDClient from "launchdarkly-node-server-sdk"'
        assert find_sdk_import(line) == "launchdarkly"

    def test_require_call(self) -> None:
        line = 'const flagsmith = require("flagsmith-nodejs")'
        assert find_sdk_import(line) == "flagsmith"

    def test_unrelated_import_returns_none(self) -> None:
        assert find_sdk_import('import React from "react"') is None


class TestFindSdkImportRubyGoJava:
    def test_ruby_require_relative(self) -> None:
        assert find_sdk_import('require_relative "unleash/client"') == "unleash"

    def test_go_single_line_import(self) -> None:
        line = 'import "github.com/launchdarkly/go-server-sdk/v6"'
        assert find_sdk_import(line) == "launchdarkly"

    def test_go_import_block_member_line(self) -> None:
        # A line from inside a Go `import (...)` block: no "import" keyword
        # on this specific line, just a lone quoted path.
        line = '    "github.com/Unleash/unleash-client-go/v4"'
        assert find_sdk_import(line) == "unleash"

    def test_java_import_static(self) -> None:
        line = "import static com.launchdarkly.sdk.LDClient.of;"
        assert find_sdk_import(line) == "launchdarkly"


class TestFindSdkImportNoneDetected:
    def test_blank_line_returns_none(self) -> None:
        assert find_sdk_import("") is None

    def test_ordinary_code_line_returns_none(self) -> None:
        assert find_sdk_import("    return x + 1") is None
