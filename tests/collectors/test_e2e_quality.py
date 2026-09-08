from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.e2e_quality import (
    RETRIES_KEY_RE,
    SHARD_KEY_RE,
    TRACE_OR_VIDEO_KEY_RE,
    _config_text_matches,
    _detect_a11y_tools,
    _detect_frameworks_from_config_files,
    _detect_frameworks_from_package_json,
    _detect_visual_regression_signals,
    _frameworks_wired_into_ci,
    _python_requirements_deps,
    _test_source_contains,
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


class TestTestSourceContains:
    """2026-09-06 extension: the test-source scan backing the
    toHaveScreenshot half of the visual-regression signal."""

    def test_finds_needle_in_spec_file(self, tmp_path: Path) -> None:
        (tmp_path / "checkout.spec.ts").write_text(
            "test('...', async () => { await expect(page).toHaveScreenshot(); });"
        )
        assert _test_source_contains(tmp_path, "toHaveScreenshot") is True

    def test_finds_needle_in_tests_directory(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "visual.ts").write_text("await expect(page).toHaveScreenshot();")
        assert _test_source_contains(tmp_path, "toHaveScreenshot") is True

    def test_ignores_non_test_source_files(self, tmp_path: Path) -> None:
        # regression guard for the exact gap this scope narrowing closes:
        # a plain source file mentioning the API (e.g. in a comment) must
        # not count as evidence a visual-regression test exists.
        (tmp_path / "utils.ts").write_text("// see toHaveScreenshot docs")
        assert _test_source_contains(tmp_path, "toHaveScreenshot") is False

    def test_no_match_returns_false(self, tmp_path: Path) -> None:
        (tmp_path / "checkout.spec.ts").write_text("test('...', () => { expect(1).toBe(1); });")
        assert _test_source_contains(tmp_path, "toHaveScreenshot") is False

    def test_non_utf8_test_file_does_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "checkout.spec.ts").write_bytes(b"\xff\xfe garbage-not-valid-utf8 toHaveScreenshot")
        assert _test_source_contains(tmp_path, "toHaveScreenshot") is True


class TestDetectVisualRegressionSignals:
    def test_percy_dependency_detected(self, tmp_path: Path) -> None:
        assert _detect_visual_regression_signals(tmp_path, {"@percy/playwright": "^1.0.0"}) == {"percy"}

    def test_chromatic_dependency_detected(self, tmp_path: Path) -> None:
        assert _detect_visual_regression_signals(tmp_path, {"chromatic": "^11.0.0"}) == {"chromatic"}

    def test_to_have_screenshot_in_test_source_detected(self, tmp_path: Path) -> None:
        (tmp_path / "visual.spec.ts").write_text("await expect(page).toHaveScreenshot();")
        assert _detect_visual_regression_signals(tmp_path, {}) == {"playwright-snapshots"}

    def test_multiple_signals_combine(self, tmp_path: Path) -> None:
        (tmp_path / "visual.spec.ts").write_text("await expect(page).toHaveScreenshot();")
        result = _detect_visual_regression_signals(tmp_path, {"chromatic": "^11.0.0"})
        assert result == {"chromatic", "playwright-snapshots"}

    def test_no_signals_returns_empty(self, tmp_path: Path) -> None:
        assert _detect_visual_regression_signals(tmp_path, {"jest": "^29.0.0"}) == set()


class TestPythonRequirementsDeps:
    def test_extracts_bare_package_names(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text(
            "axe-playwright-python==0.1.4\nrequests>=2.0\n# a comment\n\n-e ./local-pkg\n"
        )
        assert _python_requirements_deps(tmp_path) == {"axe-playwright-python", "requests"}

    def test_no_requirements_txt_returns_empty(self, tmp_path: Path) -> None:
        assert _python_requirements_deps(tmp_path) == set()

    def test_non_utf8_requirements_txt_does_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_bytes(b"axe-playwright-python==0.1.4\n\xff\xfe\n")
        assert "axe-playwright-python" in _python_requirements_deps(tmp_path)


class TestDetectA11yTools:
    def test_axe_core_playwright_js_dependency_detected(self, tmp_path: Path) -> None:
        assert _detect_a11y_tools(tmp_path, {"@axe-core/playwright": "^4.8.0"}) == {"axe-core-playwright"}

    def test_axe_playwright_python_in_requirements_txt_detected(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("axe-playwright-python==0.1.4\n")
        assert _detect_a11y_tools(tmp_path, {}) == {"axe-playwright-python"}

    def test_both_ecosystems_combine(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("axe-playwright-python==0.1.4\n")
        result = _detect_a11y_tools(tmp_path, {"@axe-core/playwright": "^4.8.0"})
        assert result == {"axe-core-playwright", "axe-playwright-python"}

    def test_no_a11y_signals_returns_empty(self, tmp_path: Path) -> None:
        assert _detect_a11y_tools(tmp_path, {}) == set()


class TestConfigTextMatches:
    """Backs flake-retry, sharding (config half), and trace/video."""

    def test_retries_key_detected_in_playwright_config(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { retries: 2 };\n")
        assert _config_text_matches(tmp_path, ["playwright", "cypress"], RETRIES_KEY_RE) is True

    def test_retries_key_detected_in_cypress_json_quoted_key(self, tmp_path: Path) -> None:
        # regression guard: cypress.json is real JSON, so the key comes
        # out quoted ("retries": 2) -- a pattern with no allowance for the
        # closing quote before the colon would silently miss this file.
        (tmp_path / "cypress.json").write_text('{"retries": 2}')
        assert _config_text_matches(tmp_path, ["playwright", "cypress"], RETRIES_KEY_RE) is True

    def test_shard_key_detected_in_playwright_config(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { shard: { total: 4, current: 1 } };\n")
        assert _config_text_matches(tmp_path, ["playwright"], SHARD_KEY_RE) is True

    def test_trace_key_detected_in_playwright_config(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("use: { trace: 'on-first-retry' },\n")
        assert _config_text_matches(tmp_path, ["playwright"], TRACE_OR_VIDEO_KEY_RE) is True

    def test_video_key_detected_in_playwright_config(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("use: { video: 'retain-on-failure' },\n")
        assert _config_text_matches(tmp_path, ["playwright"], TRACE_OR_VIDEO_KEY_RE) is True

    def test_no_matching_key_returns_false(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { timeout: 30000 };\n")
        assert _config_text_matches(tmp_path, ["playwright"], RETRIES_KEY_RE) is False

    def test_no_config_file_returns_false(self, tmp_path: Path) -> None:
        assert _config_text_matches(tmp_path, ["playwright", "cypress"], RETRIES_KEY_RE) is False

    def test_non_utf8_config_file_does_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_bytes(b"export default { \xff\xfe retries: 2 };")
        assert _config_text_matches(tmp_path, ["playwright"], RETRIES_KEY_RE) is True


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


class TestAnalyzeRepoExtendedSignals:
    """2026-09-06 extension: visual-regression, flake-retry, sharding,
    a11y-in-e2e, trace/video, and network-mock-fidelity. Each is
    independent of has_e2e_suite (see analyze_repo's own comment) --
    several tests below deliberately set up no Playwright/Cypress/
    Selenium signal at all, to prove that independence."""

    def test_visual_regression_via_percy_dependency(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@percy/playwright": "^1.0.0"}}))
        result = analyze_repo(tmp_path)
        assert result.has_visual_regression is True
        assert result.visual_regression_signals == "percy"
        assert result.has_e2e_suite is False  # proves independence from the E2E-suite signal

    def test_visual_regression_via_to_have_screenshot_in_test_source(self, tmp_path: Path) -> None:
        e2e_dir = tmp_path / "e2e"
        e2e_dir.mkdir()
        (e2e_dir / "visual.spec.ts").write_text("await expect(page).toHaveScreenshot();")
        result = analyze_repo(tmp_path)
        assert result.has_visual_regression is True
        assert result.visual_regression_signals == "playwright-snapshots"

    def test_flake_retry_config_detected(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { retries: 2 };\n")
        assert analyze_repo(tmp_path).has_flake_retry_config is True

    def test_no_flake_retry_config_is_false(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { timeout: 1000 };\n")
        assert analyze_repo(tmp_path).has_flake_retry_config is False

    def test_sharding_config_detected_via_playwright_config(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default { shard: { total: 4, current: 1 } };\n")
        assert analyze_repo(tmp_path).has_sharding_config is True

    def test_sharding_config_detected_via_ci_flag_only(self, tmp_path: Path) -> None:
        # no playwright config at all -- the CI-step-text half of this
        # signal must independently catch a --shard flag.
        yaml_text = "jobs:\n  test:\n    steps:\n      - run: npx playwright test --shard=1/4\n"
        _write_workflow(tmp_path, "ci.yml", yaml_text)
        assert analyze_repo(tmp_path).has_sharding_config is True

    def test_no_sharding_signal_is_false(self, tmp_path: Path) -> None:
        assert analyze_repo(tmp_path).has_sharding_config is False

    def test_a11y_in_e2e_detected_via_js_dependency(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@axe-core/playwright": "^4.8.0"}}))
        result = analyze_repo(tmp_path)
        assert result.has_a11y_in_e2e is True
        assert result.a11y_tools == "axe-core-playwright"

    def test_a11y_in_e2e_detected_via_python_requirements(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("axe-playwright-python==0.1.4\n")
        result = analyze_repo(tmp_path)
        assert result.has_a11y_in_e2e is True
        assert result.a11y_tools == "axe-playwright-python"

    def test_trace_or_video_config_detected(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("use: { trace: 'on-first-retry', video: 'off' },\n")
        assert analyze_repo(tmp_path).has_trace_or_video_config is True

    def test_no_trace_or_video_config_is_false(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("use: { headless: true },\n")
        assert analyze_repo(tmp_path).has_trace_or_video_config is False

    def test_network_mock_contract_fidelity_detected(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@pact-foundation/pact": "^12.0.0"}}))
        assert analyze_repo(tmp_path).has_network_mock_contract_fidelity is True

    def test_all_six_new_signals_false_on_repo_with_none_of_them(self, tmp_path: Path) -> None:
        # a repo that DOES have an E2E suite (has_e2e_suite/wired_into_ci
        # both exercised) but none of the six new signals -- the common
        # case this module will see for most real repos.
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"cypress": "^13.0.0"}}))
        result = analyze_repo(tmp_path)
        assert result.has_e2e_suite is True
        assert result.has_visual_regression is False
        assert result.visual_regression_signals == ""
        assert result.has_flake_retry_config is False
        assert result.has_sharding_config is False
        assert result.has_a11y_in_e2e is False
        assert result.a11y_tools == ""
        assert result.has_trace_or_video_config is False
        assert result.has_network_mock_contract_fidelity is False

    def test_all_six_new_signals_false_on_completely_empty_repo(self, tmp_path: Path) -> None:
        # empty-repo rung of the edge-case ladder, for the new columns
        # specifically (test_no_e2e_signals_at_all above already covers
        # the three original columns on this same input).
        result = analyze_repo(tmp_path)
        assert result.has_visual_regression is False
        assert result.has_flake_retry_config is False
        assert result.has_sharding_config is False
        assert result.has_a11y_in_e2e is False
        assert result.has_trace_or_video_config is False
        assert result.has_network_mock_contract_fidelity is False


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


class TestRunE2EQualityExtendedColumns:
    """2026-09-06 extension: proves the new columns land in the real CSV
    on disk, and that every pre-existing column is still there with its
    original meaning -- the "additive only" contract, checked end to end
    rather than just at the analyze_repo/dataclass level above."""

    def test_csv_includes_new_columns_and_preserves_existing_ones(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({
            "devDependencies": {"@playwright/test": "^1.40.0", "@axe-core/playwright": "^4.8.0"},
        }))
        (repo / "playwright.config.ts").write_text("export default { retries: 2, use: { trace: 'on' } };\n")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_e2e_quality([repo], out_dir)

        with open(out_path, newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        row = rows[0]
        # pre-existing columns, untouched
        assert row["repo"] == "repo"
        assert row["has_e2e_suite"] == "True"
        assert row["frameworks_detected"] == "playwright"
        # both package.json (the @playwright/test dep) and a
        # playwright.config.ts are present in this fixture -- "both" is
        # this pre-existing column's correct, unmodified behavior here.
        assert row["detected_via"] == "both"
        # new columns
        assert row["has_flake_retry_config"] == "True"
        assert row["has_trace_or_video_config"] == "True"
        assert row["has_a11y_in_e2e"] == "True"
        assert row["a11y_tools"] == "axe-core-playwright"
        assert row["has_visual_regression"] == "False"
        assert row["has_sharding_config"] == "False"
        assert row["has_network_mock_contract_fidelity"] == "False"
