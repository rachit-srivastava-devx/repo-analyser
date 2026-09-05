from __future__ import annotations

from pathlib import Path

from repo_analyser.core.lang import (
    DEPGRAPH_SUPPORTED,
    TEST_FILE_RE,
    TESTQUALITY_SUPPORTED,
    detect_js_test_runner,
    detect_portfolio_languages,
    detect_repo_language,
    is_internal_js_module,
    pick_unit_script,
)


def _touch(repo: Path, *names: str) -> None:
    for name in names:
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")


class TestDetectRepoLanguage:
    def test_unknown_for_empty_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty"
        repo.mkdir()
        assert detect_repo_language(repo) == "unknown"

    def test_unknown_for_only_unrecognized_extensions(self, tmp_path: Path) -> None:
        repo = tmp_path / "docs_only"
        repo.mkdir()
        _touch(repo, "README.md", "notes.txt", "data.csv")
        assert detect_repo_language(repo) == "unknown"

    def test_dominant_by_file_count(self, tmp_path: Path) -> None:
        repo = tmp_path / "mixed"
        repo.mkdir()
        _touch(repo, "a.py", "b.py", "c.py", "d.go")
        assert detect_repo_language(repo) == "python"

    def test_typescript_and_javascript_both_count_as_javascript(self, tmp_path: Path) -> None:
        repo = tmp_path / "ts_repo"
        repo.mkdir()
        _touch(repo, "a.ts", "b.tsx", "c.js")
        assert detect_repo_language(repo) == "javascript"

    def test_excludes_node_modules(self, tmp_path: Path) -> None:
        repo = tmp_path / "with_deps"
        repo.mkdir()
        _touch(repo, "app.py", "node_modules/pkg/index.js", "node_modules/pkg/lib.js",
               "node_modules/pkg/util.js")
        # without exclusion, 3 JS files would outvote 1 Python file
        assert detect_repo_language(repo) == "python"

    def test_excludes_venv_and_dist_and_build(self, tmp_path: Path) -> None:
        repo = tmp_path / "with_build"
        repo.mkdir()
        _touch(repo, "main.go", ".venv/lib/x.py", ".venv/lib/y.py", "dist/bundle.js", "build/out.js")
        assert detect_repo_language(repo) == "go"

    def test_nonexistent_path_returns_unknown_not_crash(self, tmp_path: Path) -> None:
        # rglob on a nonexistent path yields nothing rather than raising --
        # confirm we rely on that rather than crashing on a bad target.
        assert detect_repo_language(tmp_path / "does_not_exist") == "unknown"


class TestDetectPortfolioLanguages:
    def test_empty_list(self) -> None:
        assert detect_portfolio_languages([]) == set()

    def test_aggregates_and_drops_unknown(self, tmp_path: Path) -> None:
        py_repo = tmp_path / "py_repo"
        py_repo.mkdir()
        _touch(py_repo, "a.py")
        empty_repo = tmp_path / "empty_repo"
        empty_repo.mkdir()
        go_repo = tmp_path / "go_repo"
        go_repo.mkdir()
        _touch(go_repo, "main.go")
        assert detect_portfolio_languages([py_repo, empty_repo, go_repo]) == {"python", "go"}


class TestSupportedSets:
    def test_supported_sets_are_disjoint_from_unknown(self) -> None:
        # ADR-0001 in spirit: "unknown" must never be treated as a
        # supported language by a collector that gates on these sets.
        assert "unknown" not in DEPGRAPH_SUPPORTED
        assert "unknown" not in TESTQUALITY_SUPPORTED

    def test_supported_sets_are_subsets_of_known_languages(self) -> None:
        from repo_analyser.core.lang import EXT_TO_LANG
        known = set(EXT_TO_LANG.values())
        assert DEPGRAPH_SUPPORTED <= known
        assert TESTQUALITY_SUPPORTED <= known


class TestPickUnitScript:
    """Shared by testquality.py (which script to execute) and mutation.py
    (which script's body to inspect for runner detection) -- moved here
    (docs/METHODOLOGY.md #26) so both read the same choice and can never
    disagree about which JS/TS runner a repo uses."""

    def test_prefers_test_unit_over_test(self) -> None:
        assert pick_unit_script({"test": "jest", "test:unit": "vitest run"}) == "test:unit"

    def test_falls_back_to_test(self) -> None:
        assert pick_unit_script({"test": "jest", "build": "tsc"}) == "test"

    def test_none_available_returns_none(self) -> None:
        assert pick_unit_script({"build": "tsc", "lint": "eslint"}) is None

    def test_empty_scripts(self) -> None:
        assert pick_unit_script({}) is None


class TestDetectJsTestRunner:
    def test_vitest_script_body(self) -> None:
        assert detect_js_test_runner("vitest run") == "vitest"

    def test_jest_script_body(self) -> None:
        assert detect_js_test_runner("jest --coverage") == "jest"

    def test_neither_is_unknown(self) -> None:
        assert detect_js_test_runner("mocha test/**/*.js") == "unknown"

    def test_vitest_takes_precedence_if_both_present(self) -> None:
        # real-world scripts sometimes wrap one runner with a comment or a
        # migration note mentioning the other by name; vitest wins since
        # that's the actual invocation once vitest is present at all.
        assert detect_js_test_runner("vitest run # migrated from jest") == "vitest"


class TestIsInternalJsModule:
    def test_relative_path_is_internal(self) -> None:
        assert is_internal_js_module("./util.ts") is True

    def test_rooted_path_is_internal(self) -> None:
        assert is_internal_js_module("/src/util.ts") is True

    def test_node_modules_path_is_not_internal(self) -> None:
        assert is_internal_js_module("./node_modules/lodash/index.js") is False

    def test_bare_specifier_is_not_internal(self) -> None:
        # a package "exports" map resolution -- dependency-cruiser doesn't
        # always expand these to a literal node_modules/... path.
        assert is_internal_js_module("@medusajs/framework/workflows-sdk") is False


class TestTestFileRe:
    def test_matches_python_test_prefix(self) -> None:
        assert TEST_FILE_RE.search("tests/test_foo.py")
        assert TEST_FILE_RE.search("test_foo.py")

    def test_matches_python_test_suffix(self) -> None:
        assert TEST_FILE_RE.search("foo_test.py")

    def test_matches_go_test_suffix(self) -> None:
        assert TEST_FILE_RE.search("foo_test.go")

    def test_matches_js_test_and_spec_extensions(self) -> None:
        assert TEST_FILE_RE.search("foo.test.ts")
        assert TEST_FILE_RE.search("foo.spec.jsx")

    def test_matches_tests_directory_anywhere_in_path(self) -> None:
        assert TEST_FILE_RE.search("src/__tests__/helpers.ts")
        assert TEST_FILE_RE.search("tests/collectors/test_churn.py")

    def test_does_not_match_ordinary_source_file(self) -> None:
        assert not TEST_FILE_RE.search("src/repo_analyser/collectors/churn.py")
        assert not TEST_FILE_RE.search("app.py")

    def test_does_not_false_positive_on_word_containing_test(self) -> None:
        # "latest.py", "contest.py" -- "test" as a substring of a longer
        # word must not match; only a real test-file naming convention should.
        assert not TEST_FILE_RE.search("latest.py")
        assert not TEST_FILE_RE.search("contest.py")
