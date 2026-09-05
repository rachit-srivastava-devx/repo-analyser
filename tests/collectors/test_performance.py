from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_analyser.collectors.performance import (
    _detect_tools_from_config_files,
    _detect_tools_from_package_json,
    _tools_wired_into_ci,
    analyze_repo,
    run_performance,
)


class TestDetectToolsFromPackageJson:
    def test_lighthouse_ci_in_dev_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@lhci/cli": "^0.13.0"}}))
        assert _detect_tools_from_package_json(json.loads((tmp_path / "package.json").read_text())) == \
            {"lighthouse-ci"}

    def test_bundlesize_key_in_package_json(self, tmp_path: Path) -> None:
        pkg = {"bundlesize": [{"path": "./dist/*.js", "maxSize": "50kB"}]}
        assert _detect_tools_from_package_json(pkg) == {"bundlesize"}

    def test_size_limit_key_in_package_json(self, tmp_path: Path) -> None:
        pkg = {"size-limit": [{"path": "dist/index.js"}]}
        assert _detect_tools_from_package_json(pkg) == {"size-limit"}

    def test_artillery_dependency(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"artillery": "^2.0.0"}}
        assert _detect_tools_from_package_json(pkg) == {"artillery"}

    def test_unrelated_dependencies_detect_nothing(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        assert _detect_tools_from_package_json(pkg) == set()

    def test_empty_dict_returns_empty(self) -> None:
        assert _detect_tools_from_package_json({}) == set()


class TestDetectToolsFromConfigFiles:
    def test_lighthouserc_js(self, tmp_path: Path) -> None:
        (tmp_path / "lighthouserc.js").write_text("module.exports = {};\n")
        assert _detect_tools_from_config_files(tmp_path) == {"lighthouse-ci"}

    def test_artillery_yml(self, tmp_path: Path) -> None:
        (tmp_path / "artillery.yml").write_text("config: {}\n")
        assert _detect_tools_from_config_files(tmp_path) == {"artillery"}

    def test_no_config_files_returns_empty(self, tmp_path: Path) -> None:
        assert _detect_tools_from_config_files(tmp_path) == set()


class TestToolsWiredIntoCi:
    def test_lhci_autorun_step_detected(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("jobs:\n  perf:\n    steps:\n      - run: lhci autorun\n")
        assert _tools_wired_into_ci(tmp_path, {"lighthouse-ci"}) is True

    def test_no_workflows_dir_is_false(self, tmp_path: Path) -> None:
        assert _tools_wired_into_ci(tmp_path, {"lighthouse-ci"}) is False

    def test_config_present_but_not_invoked_in_ci_is_false(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("jobs:\n  build:\n    steps:\n      - run: npm run build\n")
        assert _tools_wired_into_ci(tmp_path, {"lighthouse-ci"}) is False


class TestAnalyzeRepo:
    def test_no_budget_config_reports_skip_reason_not_silent_empty(self, tmp_path: Path) -> None:
        result = analyze_repo(tmp_path)
        assert result.has_budget_config is False
        assert "no performance budget config found" in result.skip_reason

    def test_budget_config_detected_and_wired(self, tmp_path: Path) -> None:
        (tmp_path / "lighthouserc.js").write_text("module.exports = {};\n")
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("jobs:\n  perf:\n    steps:\n      - run: lhci autorun\n")
        result = analyze_repo(tmp_path)
        assert result.has_budget_config is True
        assert result.budget_tool == "lighthouse-ci"
        assert result.wired_into_ci is True
        assert result.skip_reason == ""

    def test_budget_config_present_but_not_wired(self, tmp_path: Path) -> None:
        (tmp_path / "lighthouserc.js").write_text("module.exports = {};\n")
        result = analyze_repo(tmp_path)
        assert result.has_budget_config is True
        assert result.wired_into_ci is False


class TestRunPerformance:
    def test_empty_repos_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_performance([], out_dir)
        assert list(csv.DictReader(open(out_path))) == []

    def test_writes_one_row_per_repo_with_repo_column(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()
        (repo_b / "lighthouserc.js").write_text("module.exports = {};\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_performance([repo_a, repo_b], out_dir)
        rows = {r["repo"]: r for r in csv.DictReader(open(out_path))}
        assert rows["repo-a"]["has_budget_config"] == "False"
        assert rows["repo-b"]["has_budget_config"] == "True"

    def test_writes_summary_json_with_real_counts(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        (repo_a / "lighthouserc.js").write_text("module.exports = {};\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_performance([repo_a], out_dir)
        summary = json.loads((out_dir / "performance_summary.json").read_text())
        assert summary["repos_total"] == 1
        assert summary["repos_with_budget_config"] == 1
        assert summary["repos_with_budget_wired_into_ci"] == 0
