from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.e2e_quality import (
    _detect_frameworks_from_config_files,
    _detect_frameworks_from_package_json,
    _frameworks_wired_into_ci,
    analyze_repo,
    run_e2e_quality,
)


def _write_workflow(repo: Path, name: str, yaml_text: str) -> None:
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / name).write_text(yaml_text)


class TestDetectFrameworksFromPackageJson:
    def test_playwright_in_dev_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@playwright/test": "^1.40.0"}}))
        assert _detect_frameworks_from_package_json(tmp_path) == {"playwright"}

    def test_cypress_in_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"cypress": "^13.0.0"}}))
        assert _detect_frameworks_from_package_json(tmp_path) == {"cypress"}

    def test_selenium_and_webdriverio_fold_into_one_family(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"devDependencies": {"selenium-webdriver": "^4.0.0", "webdriverio": "^8.0.0"}})
        )
        assert _detect_frameworks_from_package_json(tmp_path) == {"selenium/webdriver"}

    def test_no_package_json_returns_empty(self, tmp_path: Path) -> None:
        assert _detect_frameworks_from_package_json(tmp_path) == set()

    def test_malformed_package_json_returns_empty_not_a_crash(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not valid json")
        assert _detect_frameworks_from_package_json(tmp_path) == set()

    def test_unrelated_dependencies_detect_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"jest": "^29.0.0"}}))
        assert _detect_frameworks_from_package_json(tmp_path) == set()


class TestDetectFrameworksFromConfigFiles:
    def test_playwright_config_ts(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default {};\n")
        assert _detect_frameworks_from_config_files(tmp_path) == {"playwright"}

    def test_cypress_json_legacy_config(self, tmp_path: Path) -> None:
        (tmp_path / "cypress.json").write_text("{}")
        assert _detect_frameworks_from_config_files(tmp_path) == {"cypress"}

    def test_wdio_conf_js(self, tmp_path: Path) -> None:
        (tmp_path / "wdio.conf.js").write_text("exports.config = {};\n")
        assert _detect_frameworks_from_config_files(tmp_path) == {"selenium/webdriver"}

    def test_no_config_files_returns_empty(self, tmp_path: Path) -> None:
        assert _detect_frameworks_from_config_files(tmp_path) == set()


class TestFrameworksWiredIntoCi:
    def test_playwright_test_command_detected(self, tmp_path: Path) -> None:
        _write_workflow(tmp_path, "ci.yml", "jobs:\n  test:\n    steps:\n      - run: npx playwright test\n")
        assert _frameworks_wired_into_ci(tmp_path, {"playwright"}) is True

    def test_cypress_run_command_detected(self, tmp_path: Path) -> None:
        _write_workflow(tmp_path, "ci.yml", "jobs:\n  test:\n    steps:\n      - run: npx cypress run\n")
        assert _frameworks_wired_into_ci(tmp_path, {"cypress"}) is True

    def test_generic_test_command_is_not_mistaken_for_e2e(self, tmp_path: Path) -> None:
        # regression guard for the exact gap this module closes: ci_gates.py's
        # own broader TEST_RE would match "npm test" as *some* test command,
        # but that must not count as evidence an E2E suite specifically ran.
        _write_workflow(tmp_path, "ci.yml", "jobs:\n  test:\n    steps:\n      - run: npm test\n")
        assert _frameworks_wired_into_ci(tmp_path, {"playwright"}) is False

    def test_no_workflows_dir_is_not_wired(self, tmp_path: Path) -> None:
        assert _frameworks_wired_into_ci(tmp_path, {"playwright"}) is False

    def test_malformed_workflow_yaml_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        _write_workflow(tmp_path, "broken.yml", "not: valid: yaml: [")
        assert _frameworks_wired_into_ci(tmp_path, {"playwright"}) is False


class TestAnalyzeRepo:
    def test_no_e2e_signals_at_all(self, tmp_path: Path) -> None:
        result = analyze_repo(tmp_path)
        assert result.has_e2e_suite is False
        assert result.frameworks_detected == ""
        assert result.wired_into_ci is False

    def test_package_json_only(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"cypress": "^13.0.0"}}))
        result = analyze_repo(tmp_path)
        assert result.has_e2e_suite is True
        assert result.detected_via == "package.json"
        assert result.frameworks_detected == "cypress"

    def test_config_file_only(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default {};\n")
        result = analyze_repo(tmp_path)
        assert result.detected_via == "config_file"

    def test_both_signals_present(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"cypress": "^13.0.0"}}))
        (tmp_path / "cypress.json").write_text("{}")
        result = analyze_repo(tmp_path)
        assert result.detected_via == "both"

    def test_e2e_suite_present_and_wired_into_ci(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@playwright/test": "^1.40.0"}}))
        _write_workflow(tmp_path, "ci.yml", "jobs:\n  test:\n    steps:\n      - run: npx playwright test\n")
        result = analyze_repo(tmp_path)
        assert result.has_e2e_suite is True
        assert result.wired_into_ci is True

    def test_e2e_suite_present_but_not_wired_into_ci(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@playwright/test": "^1.40.0"}}))
        result = analyze_repo(tmp_path)
        assert result.has_e2e_suite is True
        assert result.wired_into_ci is False


class TestRunE2EQuality:
    def test_summary_counts_are_correct(self, tmp_path: Path) -> None:
        with_suite = tmp_path / "with-suite"
        with_suite.mkdir()
        (with_suite / "package.json").write_text(json.dumps({"devDependencies": {"cypress": "^13.0.0"}}))
        _write_workflow(with_suite, "ci.yml", "jobs:\n  test:\n    steps:\n      - run: npx cypress run\n")

        no_suite = tmp_path / "no-suite"
        no_suite.mkdir()

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_e2e_quality([with_suite, no_suite], out_dir)

        summary = json.loads((out_dir / "e2e_quality_summary.json").read_text())
        assert summary == {"repos_total": 2, "repos_with_e2e_suite": 1, "repos_with_e2e_wired_into_ci": 1}
