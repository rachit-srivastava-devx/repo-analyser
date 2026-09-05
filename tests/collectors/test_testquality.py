from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors.testquality import (
    _analyze_go_repo,
    _analyze_python_repo,
    _parse_junit_xml,
    _parse_output,
    _pytest_command,
    analyze_repo,
    run_testquality,
)

HAS_GO = subprocess.run(["which", "go"], capture_output=True).returncode == 0


class TestPytestCommand:
    def test_prefers_repos_own_dot_venv(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        venv_pytest = repo / ".venv" / "bin" / "pytest"
        venv_pytest.parent.mkdir(parents=True)
        venv_pytest.write_text("#!/bin/sh\n")
        assert _pytest_command(repo) == [str(venv_pytest)]

    def test_falls_back_to_venv_dir_name(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        venv_pytest = repo / "venv" / "bin" / "pytest"
        venv_pytest.parent.mkdir(parents=True)
        venv_pytest.write_text("#!/bin/sh\n")
        assert _pytest_command(repo) == [str(venv_pytest)]

    def test_no_repo_venv_falls_back_to_path_or_module(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        cmd = _pytest_command(repo)
        assert cmd == ["pytest"] or cmd == ["python3", "-m", "pytest"]


class TestParseJunitXml:
    """Fixtures are real pytest --junit-xml output, captured directly (not
    hand-written), for exactly the two shapes that used to require three
    separate regexes to distinguish: a normal mixed run, and a pure
    collection failure."""

    def test_mixed_pass_fail(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "junit.xml"
        xml_path.write_text(
            '<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
            '<testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="0.025">'
            '<testcase classname="test_sample" name="test_ok" time="0.001" />'
            '<testcase classname="test_sample" name="test_fail" time="0.001">'
            '<failure message="assert 1 == 2">AssertionError</failure></testcase>'
            "</testsuite></testsuites>"
        )
        passed, failed, total, errors = _parse_junit_xml(xml_path)
        assert (passed, failed, total, errors) == (1, 1, 2, 0)

    def test_pure_collection_error(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "junit.xml"
        xml_path.write_text(
            '<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
            '<testsuite name="pytest" errors="1" failures="0" skipped="0" tests="1" time="0.11">'
            '<testcase classname="" name="test_broken" time="0.0">'
            '<error message="collection failure">ModuleNotFoundError</error></testcase>'
            "</testsuite></testsuites>"
        )
        passed, failed, total, errors = _parse_junit_xml(xml_path)
        assert (passed, failed, total, errors) == (0, 1, 1, 1)

    def test_all_passed_with_skips(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "junit.xml"
        xml_path.write_text(
            '<testsuites><testsuite errors="0" failures="0" skipped="2" tests="5">'
            "</testsuite></testsuites>"
        )
        assert _parse_junit_xml(xml_path) == (3, 0, 5, 0)

    def test_bare_testsuite_root_no_wrapper(self, tmp_path: Path) -> None:
        # some pytest/plugin versions emit <testsuite> as the document root
        # directly, without the outer <testsuites> wrapper.
        xml_path = tmp_path / "junit.xml"
        xml_path.write_text('<testsuite errors="0" failures="0" skipped="0" tests="1"></testsuite>')
        assert _parse_junit_xml(xml_path) == (1, 0, 1, 0)

    def test_missing_testsuite_element_returns_zeros_not_crash(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "junit.xml"
        xml_path.write_text("<testsuites></testsuites>")
        assert _parse_junit_xml(xml_path) == (0, 0, 0, 0)


class TestParseOutputVitest:
    def test_all_passed_format(self) -> None:
        # real vitest format 1: "Tests  12 passed (12)"
        text = "Test Files  3 passed (3)\n     Tests  12 passed (12)\n"
        passed, failed, total, mode = _parse_output("vitest", text)
        assert (passed, failed, total, mode) == (12, 0, 12, "")

    def test_mixed_format(self) -> None:
        # real vitest format 2: "Tests  3 failed | 9 passed (12)"
        text = "     Tests  3 failed | 9 passed (12)\n"
        passed, failed, total, mode = _parse_output("vitest", text)
        assert (passed, failed, total, mode) == (9, 3, 12, "")

    def test_all_failed_format_no_passed_segment(self) -> None:
        # the historical bug: this exact format ("1 failed (1)", no "passed"
        # segment at all) produced 0/0/0 with an earlier, narrower regex,
        # silently hiding a real failure.
        text = "     Tests  1 failed (1)\n"
        passed, failed, total, mode = _parse_output("vitest", text)
        assert (passed, failed, total, mode) == (0, 1, 1, "")

    def test_no_summary_line_reports_failure_mode_not_silent_zero(self) -> None:
        passed, failed, total, mode = _parse_output("vitest", "some unrelated crash output\n")
        assert (passed, failed, total) == (0, 0, 0)
        assert "no 'Tests' summary line" in mode


class TestParseOutputJest:
    def test_all_passed(self) -> None:
        text = "Tests:       12 passed, 12 total\n"
        passed, failed, total, mode = _parse_output("jest", text)
        assert (passed, failed, total, mode) == (12, 0, 12, "")

    def test_mixed_with_failed_and_skipped(self) -> None:
        text = "Tests:       2 failed, 1 skipped, 9 passed, 12 total\n"
        passed, failed, total, mode = _parse_output("jest", text)
        assert (passed, failed, total, mode) == (9, 2, 12, "")

    def test_config_validation_error_is_a_named_failure_mode(self) -> None:
        text = "●  Validation Error:\n\n  Configuration error"
        passed, failed, total, mode = _parse_output("jest", text)
        assert (passed, failed, total) == (0, 0, 0)
        assert "config validation error" in mode

    def test_no_tests_found_is_a_named_failure_mode_distinct_from_config_error(self) -> None:
        text = "No tests found, exiting with code 1"
        passed, failed, total, mode = _parse_output("jest", text)
        assert (passed, failed, total) == (0, 0, 0)
        assert "no tests written" in mode
        assert "config" not in mode

    def test_no_summary_line_reports_failure_mode(self) -> None:
        passed, failed, total, mode = _parse_output("jest", "unrelated crash\n")
        assert (passed, failed, total) == (0, 0, 0)
        assert mode != ""


class TestParseOutputUnrecognizedRunner:
    def test_unknown_runner_reports_failure_mode_not_silent_zero(self) -> None:
        passed, failed, total, mode = _parse_output("mocha", "12 passing\n")
        assert (passed, failed, total) == (0, 0, 0)
        assert "unrecognized runner" in mode
        assert "mocha" in mode


class TestAnalyzePythonRepoRealExecution:
    """Real pytest execution, not mocked output -- this is exactly the
    property this module exists to verify for target repos, so its own
    tests hold it to the same bar."""

    def test_all_tests_pass(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_math.py").write_text("def test_add():\n    assert 1 + 1 == 2\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert result.ran is True
        assert result.exit_code == 0
        assert result.tests_passed == 1
        assert result.tests_failed == 0
        assert result.failure_mode == ""

    def test_a_real_failure_is_reported_not_hidden(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_math.py").write_text("def test_add():\n    assert 1 + 1 == 3\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert result.exit_code != 0
        assert result.tests_failed == 1
        assert result.tests_passed == 0

    def test_import_error_is_a_named_failure_mode(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_broken.py").write_text("import this_module_does_not_exist_xyz\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert "import error" in result.failure_mode

    def test_collection_error_is_not_miscounted_as_a_failed_test(self, tmp_path: Path) -> None:
        # regression test for a real bug found while writing this suite:
        # pytest's --tb=no short summary for a collection-time import error
        # ("1 error during collection") matched PYTEST_SUMMARY_RE's generic
        # `errors` group and was reported as tests_failed=1/tests_total=1 --
        # indistinguishable from "one real test ran and failed an assertion".
        # It must report 0/0/0 with the import-error failure_mode instead.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_broken.py").write_text("import this_module_does_not_exist_xyz\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert result.tests_total == 0
        assert result.tests_failed == 0
        assert "import error" in result.failure_mode

    def test_collection_error_aborts_even_a_passing_sibling_test(self, tmp_path: Path) -> None:
        # pytest's default is to abort the whole session on a collection
        # error, not just skip the broken file -- a real passing test next
        # to a broken-import file still reports zero tests executed.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_broken.py").write_text("import this_module_does_not_exist_xyz\n")
        (repo / "test_ok.py").write_text("def test_ok():\n    assert True\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert result.tests_total == 0
        assert "import error" in result.failure_mode

    def test_no_test_files_is_skipped_not_a_fake_pass(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("x = 1\n")
        result = _analyze_python_repo(repo, timeout=30, log_dir=None)
        assert result.ran is False
        assert "no test_*.py" in result.skip_reason

    def test_log_dir_captures_real_output(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test_x.py").write_text("def test_x():\n    assert True\n")
        log_dir = tmp_path / "logs"
        _analyze_python_repo(repo, timeout=30, log_dir=log_dir)
        assert (log_dir / "repo.log").exists()
        assert "1 passed" in (log_dir / "repo.log").read_text()


@pytest.mark.skipif(not HAS_GO, reason="go toolchain not on PATH")
class TestAnalyzeGoRepoRealExecution:
    def test_all_tests_pass(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module example.com/repo\n\ngo 1.21\n")
        (repo / "add.go").write_text("package main\n\nfunc Add(a, b int) int { return a + b }\n")
        (repo / "add_test.go").write_text(
            'package main\n\nimport "testing"\n\n'
            'func TestAdd(t *testing.T) {\n    if Add(1, 1) != 2 {\n        t.Fail()\n    }\n}\n'
        )
        result = _analyze_go_repo(repo, timeout=60, log_dir=None)
        assert result.ran is True
        assert result.tests_passed == 1
        assert result.tests_failed == 0

    def test_a_real_failure_is_reported(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module example.com/repo\n\ngo 1.21\n")
        (repo / "bad_test.go").write_text(
            'package main\n\nimport "testing"\n\nfunc TestFails(t *testing.T) {\n    t.Fail()\n}\n'
        )
        result = _analyze_go_repo(repo, timeout=60, log_dir=None)
        assert result.tests_failed == 1

    def test_no_go_mod_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _analyze_go_repo(repo, timeout=30, log_dir=None)
        assert result.ran is False
        assert "no go.mod" in result.skip_reason

    def test_no_test_files_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module example.com/repo\n\ngo 1.21\n")
        (repo / "main.go").write_text("package main\n\nfunc main() {}\n")
        result = _analyze_go_repo(repo, timeout=30, log_dir=None)
        assert result.ran is False
        assert "no *_test.go" in result.skip_reason


class TestAnalyzeRepoDispatch:
    def test_unsupported_language_names_what_is_supported(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Main.java").write_text("")
        result = analyze_repo(repo)
        assert "not supported" in result.skip_reason
        assert "python" in result.skip_reason


class TestRunTestquality:
    def test_summary_counts_are_internally_consistent(self, tmp_path: Path) -> None:
        passing_repo = tmp_path / "passing"
        passing_repo.mkdir()
        (passing_repo / "test_ok.py").write_text("def test_ok():\n    assert True\n")
        no_tests_repo = tmp_path / "no_tests"
        no_tests_repo.mkdir()
        (no_tests_repo / "app.py").write_text("")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        tmp_dir = tmp_path / "_tmp"
        run_testquality([passing_repo, no_tests_repo], out_dir, tmp_dir)

        import json
        summary = json.loads((out_dir / "testquality_summary.json").read_text())
        assert summary["total_repos"] == 2
        assert summary["repos_with_unit_script"] == 1
        assert summary["repos_all_tests_passing"] == 1
        assert summary["repos_skipped_no_script"] == 1
        assert "no_tests" in summary["skip_reasons"]
