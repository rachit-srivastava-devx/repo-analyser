from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors.mutation import (
    _analyze_js_repo,
    _analyze_python_repo,
    _detect_js_runner,
    _detect_tests_dir,
    _install_stryker,
    _mutmut_setup_cfg_text,
    _parse_mutmut_results,
    analyze_repo,
    run_mutation,
    select_mutation_targets,
)
from repo_analyser.core.util import RunResult

HAS_MUTMUT = subprocess.run(["which", "mutmut"], capture_output=True).returncode == 0


class TestParseMutmutResults:
    """Grounded against mutmut 3.3.1's real `status_by_exit_code` vocabulary
    (mutmut/__main__.py) -- not inferred from a single sample run."""

    def test_single_killed(self) -> None:
        assert _parse_mutmut_results("    calc.x_add__mutmut_1: killed\n") == {"killed": 1}

    def test_all_real_statuses(self) -> None:
        text = "\n".join([
            "mod.x_a__mutmut_1: killed",
            "mod.x_b__mutmut_1: survived",
            "mod.x_c__mutmut_1: timeout",
            "mod.x_d__mutmut_1: suspicious",
            "mod.x_e__mutmut_1: skipped",
            "mod.x_f__mutmut_1: no tests",
            "mod.x_g__mutmut_1: segfault",
        ])
        counts = _parse_mutmut_results(text)
        assert counts == {
            "killed": 1, "survived": 1, "timeout": 1, "suspicious": 1,
            "skipped": 1, "no_tests": 1, "segfault": 1,
        }

    def test_multiword_status_underscored(self) -> None:
        assert _parse_mutmut_results("x.y__mutmut_1: no tests\n") == {"no_tests": 1}

    def test_repeated_status_counted(self) -> None:
        text = "a.x__mutmut_1: killed\na.x__mutmut_2: killed\na.x__mutmut_3: survived\n"
        assert _parse_mutmut_results(text) == {"killed": 2, "survived": 1}

    def test_empty_text_returns_empty(self) -> None:
        assert _parse_mutmut_results("") == {}

    def test_leading_whitespace_and_indentation_tolerated(self) -> None:
        # mutmut's real CLI output indents each line with 4 spaces.
        assert _parse_mutmut_results("    a.x__mutmut_1: killed") == {"killed": 1}

    def test_unrelated_lines_are_ignored(self) -> None:
        text = "Some header text\n\na.x__mutmut_1: killed\n\nDone.\n"
        assert _parse_mutmut_results(text) == {"killed": 1}


class TestDetectTestsDir:
    def test_prefers_tests_over_test(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "test").mkdir()
        assert _detect_tests_dir(tmp_path) == "tests"

    def test_falls_back_to_test(self, tmp_path: Path) -> None:
        (tmp_path / "test").mkdir()
        assert _detect_tests_dir(tmp_path) == "test"

    def test_no_test_dir_falls_back_to_repo_root(self, tmp_path: Path) -> None:
        assert _detect_tests_dir(tmp_path) == "."


class TestMutmutSetupCfgText:
    def test_contains_target_file_and_tests_dir(self) -> None:
        text = _mutmut_setup_cfg_text("app.py", "tests")
        assert "[mutmut]" in text
        assert "paths_to_mutate=app.py" in text
        assert "tests_dir=tests" in text

    def test_forces_use_setproctitle_off(self) -> None:
        # Regression test for docs/METHODOLOGY.md #23: mutmut's
        # setproctitle dependency is fork-unsafe on macOS and crashed the
        # host during a real portfolio run. This must never be silently
        # dropped from the generated config again.
        text = _mutmut_setup_cfg_text("app.py", "tests")
        assert "use_setproctitle=False" in text


class TestAnalyzePythonRepoSkipPaths:
    def test_target_file_not_found(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _analyze_python_repo(repo, "does_not_exist.py")
        assert result.ran is False
        assert "target file not found" in result.skip_reason

    def test_mutmut_not_on_path(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("x = 1\n")
        monkeypatch.setattr("shutil.which", lambda name: None)
        result = _analyze_python_repo(repo, "app.py")
        assert result.ran is False
        assert "mutmut not on PATH" in result.skip_reason


class TestAnalyzeRepoDispatch:
    def test_unsupported_language_names_what_is_supported(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Main.java").write_text("")
        result = analyze_repo(repo, "Main.java")
        assert "not supported" in result.skip_reason
        assert "python" in result.skip_reason


@pytest.mark.skipif(not HAS_MUTMUT, reason="mutmut not on PATH")
class TestAnalyzePythonRepoRealExecution:
    def test_setup_cfg_is_restored_verbatim_when_repo_already_has_one(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_calc.py").write_text(
            "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        )
        original_cfg = "[flake8]\nmax-line-length = 100\n"
        (repo / "setup.cfg").write_text(original_cfg)

        _analyze_python_repo(repo, "calc.py", tmp_dir=tmp_path / "tmp")

        assert (repo / "setup.cfg").read_text() == original_cfg
        assert not (repo / "mutants").exists()  # scratch dir cleaned up

    def test_no_preexisting_setup_cfg_is_removed_after(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_calc.py").write_text(
            "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        )
        assert not (repo / "setup.cfg").exists()

        _analyze_python_repo(repo, "calc.py", tmp_dir=tmp_path / "tmp")

        assert not (repo / "setup.cfg").exists()

    def test_a_file_with_zero_test_coverage_reports_no_coverage_not_a_silent_zero(self, tmp_path: Path) -> None:
        # regression test for a real finding from dogfooding this tool on
        # its own reporting/charts.py (0% covered): mutmut aborts the
        # whole file early ("Stopping early, because we could not find
        # any test case for any mutant") and reports every mutant as
        # "not_checked", not the per-mutant "no tests" status -- both must
        # fold into no_coverage, not vanish into an unaccounted total.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "uncovered.py").write_text("def add(a, b):\n    return a + b\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_other.py").write_text(
            "def test_unrelated():\n    assert True\n"
        )
        result = _analyze_python_repo(repo, "uncovered.py", tmp_dir=tmp_path / "tmp")
        assert result.ran is True
        assert result.total_mutants >= 1
        assert result.no_coverage == result.total_mutants
        assert result.killed == 0
        assert result.survived == 0

    def test_real_run_produces_internally_consistent_counts(self, tmp_path: Path) -> None:
        # Not asserting a specific killed/survived split: this exact
        # environment has an observed, root-caused platform quirk (see
        # module docstring) where a killable mutant can report as
        # "segfault" instead of "killed". The invariant that must always
        # hold regardless of that quirk is that every mutant lands in
        # exactly one counted bucket.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_calc.py").write_text(
            "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        )
        result = _analyze_python_repo(repo, "calc.py", tmp_dir=tmp_path / "tmp")
        assert result.ran is True
        assert result.total_mutants >= 1
        accounted = (result.killed + result.survived + result.no_coverage +
                     result.timeout + result.suspicious + result.segfault)
        assert accounted == result.total_mutants


class TestDetectJsRunner:
    """Regression coverage for docs/METHODOLOGY.md #26: mutation.py used to
    hardcode `testRunner: "jest"` with zero detection."""

    def test_no_package_json_is_unknown(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        assert _detect_js_runner(repo) == "unknown"

    def test_no_unit_script_is_unknown(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({"scripts": {"build": "tsc"}}))
        assert _detect_js_runner(repo) == "unknown"

    def test_detects_vitest_from_script_body(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}))
        assert _detect_js_runner(repo) == "vitest"

    def test_detects_jest_from_script_body(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({"scripts": {"test": "jest --coverage"}}))
        assert _detect_js_runner(repo) == "jest"

    def test_agrees_with_the_same_script_testquality_would_pick(self, tmp_path: Path) -> None:
        # the exact hardcoding-audit scenario: a repo with both a plain
        # "test" (jest) and a "test:unit" (vitest) script -- mutation.py
        # must key off test:unit, same as testquality.py's pick_unit_script,
        # or the two modules could disagree about which runner is real.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest", "test:unit": "vitest run"}})
        )
        assert _detect_js_runner(repo) == "vitest"


class TestInstallStrykerPackageSelection:
    """Regression coverage for docs/METHODOLOGY.md #26: only the jest
    plugin was ever installed, regardless of detected runner."""

    def _stub_successful_install(self, monkeypatch, repo: Path) -> dict:
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            binary = repo / "node_modules" / ".bin" / "stryker"
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text("#!/bin/sh\n")
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr("repo_analyser.collectors.mutation.run", fake_run)
        return captured

    def test_jest_runner_installs_jest_plugin_only(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        captured = self._stub_successful_install(monkeypatch, repo)
        assert _install_stryker(repo, "jest") is True
        assert "@stryker-mutator/jest-runner" in captured["cmd"]
        assert "@stryker-mutator/vitest-runner" not in captured["cmd"]

    def test_vitest_runner_installs_vitest_plugin_only(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        captured = self._stub_successful_install(monkeypatch, repo)
        assert _install_stryker(repo, "vitest") is True
        assert "@stryker-mutator/vitest-runner" in captured["cmd"]
        assert "@stryker-mutator/jest-runner" not in captured["cmd"]

    def test_install_has_scripts_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # security regression test (docs/ARCHITECTURE.md "Security model"):
        # this installs a tool-chosen, trusted package *inside* whatever
        # arbitrary target repo this tool is pointed at -- a compromised
        # repo's own .npmrc/registry config could otherwise try to hijack
        # the install via a postinstall script.
        repo = tmp_path / "repo"
        repo.mkdir()
        captured = self._stub_successful_install(monkeypatch, repo)
        _install_stryker(repo, "jest")
        assert "--ignore-scripts" in captured["cmd"]


class TestAnalyzeJsRepoConfigBuilding:
    """Fast, mocked tests for the runner-detection/config-building logic
    fixed by docs/METHODOLOGY.md #26/#27 -- no real npm install or Stryker
    run (a real end-to-end run is verified separately, manually, since it
    needs a real network npm install). These only confirm the JSON Stryker
    is handed, and the environment it runs in, are shaped correctly."""

    def _repo_with_script(self, tmp_path: Path, name: str, script_body: str) -> Path:
        repo = tmp_path / name
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({"scripts": {"test": script_body}}))
        (repo / "target.js").write_text("module.exports = 1;\n")
        return repo

    def _stub_stryker_binary_run(self, monkeypatch, returncode: int = 1, capture: dict | None = None):
        monkeypatch.setattr("repo_analyser.collectors.mutation._install_stryker",
                             lambda repo, runner: True)

        def fake_subprocess_run(*args, **kwargs):
            if capture is not None:
                capture["env"] = kwargs.get("env") or {}
            return subprocess.CompletedProcess(args[0] if args else [], returncode, "", "")

        monkeypatch.setattr("repo_analyser.collectors.mutation.subprocess.run", fake_subprocess_run)

    def test_vitest_repo_gets_vitest_test_runner_and_no_jest_key(self, tmp_path: Path, monkeypatch) -> None:
        repo = self._repo_with_script(tmp_path, "vrepo", "vitest run")
        self._stub_stryker_binary_run(monkeypatch)
        tmp_dir = tmp_path / "tmp"
        _analyze_js_repo(repo, "target.js", tmp_dir=tmp_dir)
        config = json.loads((tmp_dir / f"{repo.name}.stryker.json").read_text())
        assert config["testRunner"] == "vitest"
        assert "jest" not in config
        # regression test for docs/METHODOLOGY.md #26's second finding: a
        # real end-to-end run against a real vitest fixture still failed
        # with "No tests were executed" under Stryker's own default
        # `related: true`, even though the fixture's test directly imports
        # its source file -- a documented Stryker unreliability, not
        # guessed. Must stay explicitly disabled.
        assert config["vitest"]["related"] is False

    def test_jest_repo_gets_jest_test_runner_and_config_file(self, tmp_path: Path, monkeypatch) -> None:
        repo = self._repo_with_script(tmp_path, "jrepo", "jest --coverage")
        self._stub_stryker_binary_run(monkeypatch)
        tmp_dir = tmp_path / "tmp"
        _analyze_js_repo(repo, "target.js", tmp_dir=tmp_dir)
        config = json.loads((tmp_dir / f"{repo.name}.stryker.json").read_text())
        assert config["testRunner"] == "jest"
        assert config["jest"]["configFile"] == "jest.config.js"

    def test_unknown_runner_is_a_named_skip_not_a_silent_jest_guess(self, tmp_path: Path) -> None:
        repo = self._repo_with_script(tmp_path, "mrepo", "mocha 'test/**/*.js'")
        result = _analyze_js_repo(repo, "target.js", tmp_dir=tmp_path / "tmp")
        assert result.ran is False
        assert "could not detect jest vs vitest" in result.skip_reason

    def test_default_test_type_env_is_the_real_env_var_name(self) -> None:
        # regression test for docs/METHODOLOGY.md #27: the old default
        # ("unit") set an env var literally *named* "unit", never TEST_TYPE.
        import inspect
        assert inspect.signature(_analyze_js_repo).parameters["test_type_env"].default == "TEST_TYPE"
        assert inspect.signature(analyze_repo).parameters["test_type_env"].default == "TEST_TYPE"

    def test_env_extra_is_applied_for_jest(self, tmp_path: Path, monkeypatch) -> None:
        import os
        repo = self._repo_with_script(tmp_path, "jrepo2", "jest --coverage")
        capture: dict = {}
        self._stub_stryker_binary_run(monkeypatch, capture=capture)
        _analyze_js_repo(repo, "target.js", tmp_dir=tmp_path / "tmp")
        assert capture["env"].get("TEST_TYPE") == "unit"
        assert set(capture["env"]) - set(os.environ) == {"TEST_TYPE"}

    def test_no_mutation_json_skip_reason_captures_the_head_not_just_the_tail(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # regression test for docs/METHODOLOGY.md #31: a real Node.js
        # uncaught-exception dump (the exact shape captured, truncated, in
        # analyses/posx_after/FINDINGS.md §11) prints the real error
        # type/message FIRST, then a long stack trace, then the engine
        # version LAST -- a tail slice loses the one line that would have
        # named the real cause.
        repo = self._repo_with_script(tmp_path, "crashrepo", "jest --coverage")
        monkeypatch.setattr("repo_analyser.collectors.mutation._install_stryker",
                             lambda repo, runner: True)
        fake_error = "TypeError: Cannot read properties of undefined (reading 'foo')"
        padding = "\n".join(f"    at frame{i} (file.js:{i}:1)" for i in range(200))
        crash_output = f"{fake_error}\n{padding}\n  innerError: undefined\n}}\n\nNode.js v20.20.2\n"
        assert len(crash_output) > 2500  # long enough that a [-500:] slice would miss fake_error entirely

        def fake_subprocess_run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0] if args else [], 1, crash_output, "")

        monkeypatch.setattr("repo_analyser.collectors.mutation.subprocess.run", fake_subprocess_run)
        result = _analyze_js_repo(repo, "target.js", tmp_dir=tmp_path / "tmp")
        assert result.ran is False
        assert fake_error in result.skip_reason

    def test_env_extra_is_not_applied_for_vitest(self, tmp_path: Path, monkeypatch) -> None:
        import os
        repo = self._repo_with_script(tmp_path, "vrepo2", "vitest run")
        capture: dict = {}
        self._stub_stryker_binary_run(monkeypatch, capture=capture)
        _analyze_js_repo(repo, "target.js", tmp_dir=tmp_path / "tmp")
        assert set(capture["env"]) - set(os.environ) == set()


class TestSelectMutationTargets:
    def test_raises_if_prerequisite_csvs_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="testquality_runs.csv"):
            select_mutation_targets(tmp_path, [])

    def test_only_fully_passing_repos_are_selected(self, tmp_path: Path) -> None:
        with open(tmp_path / "testquality_runs.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "ran", "exit_code", "tests_total"])
            w.writerow(["passing-repo", "True", "0", "10"])
            w.writerow(["failing-repo", "True", "1", "10"])
            w.writerow(["no-tests-repo", "True", "0", "0"])
        with open(tmp_path / "complexity_hotspots.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "file", "hotspot_score"])
            w.writerow(["passing-repo", "hot.py", "500"])
            w.writerow(["failing-repo", "hot.py", "500"])
            w.writerow(["no-tests-repo", "hot.py", "500"])

        repos = [tmp_path / n for n in ("passing-repo", "failing-repo", "no-tests-repo")]
        targets = select_mutation_targets(tmp_path, repos)
        assert len(targets) == 1
        assert targets[0][0].name == "passing-repo"
        assert targets[0][1] == "hot.py"

    def test_picks_the_single_highest_hotspot_per_repo(self, tmp_path: Path) -> None:
        with open(tmp_path / "testquality_runs.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "ran", "exit_code", "tests_total"])
            w.writerow(["r", "True", "0", "10"])
        with open(tmp_path / "complexity_hotspots.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "file", "hotspot_score"])
            w.writerow(["r", "cold.py", "10"])
            w.writerow(["r", "hot.py", "999"])
            w.writerow(["r", "medium.py", "500"])

        targets = select_mutation_targets(tmp_path, [tmp_path / "r"])
        assert targets == [(tmp_path / "r", "hot.py")]

    def test_repo_with_no_hotspot_row_is_not_selected(self, tmp_path: Path) -> None:
        with open(tmp_path / "testquality_runs.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "ran", "exit_code", "tests_total"])
            w.writerow(["r", "True", "0", "10"])
        with open(tmp_path / "complexity_hotspots.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "file", "hotspot_score"])
        assert select_mutation_targets(tmp_path, [tmp_path / "r"]) == []

    def test_test_files_are_excluded_even_when_they_top_the_hotspot_ranking(self, tmp_path: Path) -> None:
        # regression test for a real bug found by dogfooding: this tool's
        # own test-heavy portfolio had a test file as its #1 hotspot, and
        # mutating it produced a meaningless all-"skipped" result.
        with open(tmp_path / "testquality_runs.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "ran", "exit_code", "tests_total"])
            w.writerow(["r", "True", "0", "10"])
        with open(tmp_path / "complexity_hotspots.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "file", "hotspot_score"])
            w.writerow(["r", "tests/test_app.py", "999"])  # highest score, but a test file
            w.writerow(["r", "app.py", "500"])

        targets = select_mutation_targets(tmp_path, [tmp_path / "r"])
        assert targets == [(tmp_path / "r", "app.py")]

    def test_repo_whose_only_hotspot_is_a_test_file_is_not_selected(self, tmp_path: Path) -> None:
        with open(tmp_path / "testquality_runs.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "ran", "exit_code", "tests_total"])
            w.writerow(["r", "True", "0", "10"])
        with open(tmp_path / "complexity_hotspots.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["repo", "file", "hotspot_score"])
            w.writerow(["r", "tests/test_app.py", "999"])
        assert select_mutation_targets(tmp_path, [tmp_path / "r"]) == []


class TestRunMutation:
    def test_empty_targets_writes_valid_empty_output(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_mutation([], out_dir, tmp_path / "tmp")
        assert out_path.exists()
        import json
        summary = json.loads((out_dir / "mutation_summary.json").read_text())
        assert summary["repos_attempted"] == 0
        assert summary["mean_mutation_score"] is None

    def test_unsupported_language_target_is_recorded_as_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Main.java").write_text("")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_mutation([(repo, "Main.java")], out_dir, tmp_path / "tmp")
        import json
        summary = json.loads((out_dir / "mutation_summary.json").read_text())
        assert summary["repos_succeeded"] == 0
        assert "not supported" in summary["skip_reasons"]["repo"]
