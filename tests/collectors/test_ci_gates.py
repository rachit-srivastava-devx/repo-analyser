from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyser.collectors.ci_gates import (
    _workflow_is_deploy_only,
    _workflow_runs_tests,
    analyze_repo,
    run_ci_gates,
)


def _write_workflow(repo: Path, name: str, content: str) -> None:
    d = repo / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content)


class TestWorkflowRunsTests:
    def test_npm_test_run_step(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "npm test"}]}}}
        assert _workflow_runs_tests(doc) is True

    def test_npm_run_test_colon_subscript(self) -> None:
        # the specific pattern this tool needed to catch "npm run test:unit"
        doc = {"jobs": {"build": {"steps": [{"run": "npm run test:unit"}]}}}
        assert _workflow_runs_tests(doc) is True

    def test_deploy_only_workflow_has_no_test_step(self) -> None:
        doc = {"jobs": {"deploy": {"steps": [{"run": "docker build -t app ."},
                                              {"run": "aws ecs update-service"}]}}}
        assert _workflow_runs_tests(doc) is False

    def test_bash_conditional_test_dash_f_is_not_a_false_positive(self) -> None:
        # "test -f file.txt" (bash file-test operator) must not match --
        # this is exactly why the patterns are word-boundary + command-shaped.
        doc = {"jobs": {"build": {"steps": [{"run": "if test -f file.txt; then echo ok; fi"}]}}}
        assert _workflow_runs_tests(doc) is False

    def test_uses_field_can_also_indicate_tests(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"uses": "cypress-io/github-action@v6", "with": {}}]}}}
        # cypress-io/github-action doesn't match "cypress run" textually in `uses`,
        # so this specifically checks a step with no run/uses test signal at all is False,
        # and a run step invoking playwright is True.
        assert _workflow_runs_tests(doc) is False
        doc2 = {"jobs": {"build": {"steps": [{"run": "npx playwright test"}]}}}
        assert _workflow_runs_tests(doc2) is True

    def test_empty_doc_is_false(self) -> None:
        assert _workflow_runs_tests({}) is False
        assert _workflow_runs_tests(None) is False

    def test_non_dict_step_does_not_crash(self) -> None:
        doc = {"jobs": {"build": {"steps": ["not-a-dict", {"run": "npm test"}]}}}
        assert _workflow_runs_tests(doc) is True

    def test_non_dict_job_does_not_crash(self) -> None:
        doc = {"jobs": {"build": "not-a-dict"}}
        assert _workflow_runs_tests(doc) is False


class TestWorkflowIsDeployOnly:
    def test_detects_kubectl(self) -> None:
        doc = {"jobs": {"deploy": {"steps": [{"run": "kubectl apply -f k8s/"}]}}}
        assert _workflow_is_deploy_only(doc) is True

    def test_no_deploy_hints_is_false(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "npm ci"}]}}}
        assert _workflow_is_deploy_only(doc) is False


class TestAnalyzeRepo:
    def test_no_workflows_dir(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = analyze_repo(repo)
        assert result.has_ci_config is False
        assert result.workflow_count == 0

    def test_deploy_only_workflow_is_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_workflow(repo, "deploy.yml", """
on:
  push:
    branches: [main]
jobs:
  deploy:
    steps:
      - run: docker build -t app .
      - run: aws ecs update-service --force-new-deployment
""")
        result = analyze_repo(repo)
        assert result.has_ci_config is True
        assert result.any_workflow_runs_tests is False
        assert result.all_workflows_deploy_only is True

    def test_workflow_with_tests_is_not_flagged_deploy_only(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_workflow(repo, "ci.yml", """
on: [pull_request]
jobs:
  test:
    steps:
      - run: npm ci
      - run: npm test
""")
        result = analyze_repo(repo)
        assert result.any_workflow_runs_tests is True
        assert result.all_workflows_deploy_only is False

    def test_bare_on_key_parsed_as_true_is_still_captured(self, tmp_path: Path) -> None:
        # YAML 1.1 loaders parse a bare `on:` key as the boolean True in
        # some configurations -- this must still populate triggers, not
        # silently drop them.
        repo = tmp_path / "repo"
        _write_workflow(repo, "ci.yml", """
on:
  push: {}
  pull_request: {}
jobs:
  test:
    steps:
      - run: npm test
""")
        result = analyze_repo(repo)
        assert "push" in result.triggers
        assert "pull_request" in result.triggers

    def test_string_trigger(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_workflow(repo, "ci.yml", "on: push\njobs:\n  test:\n    steps:\n      - run: npm test\n")
        result = analyze_repo(repo)
        assert result.triggers == "push"

    def test_malformed_yaml_raises_not_silently_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_workflow(repo, "broken.yml", "jobs:\n  test:\n    steps: [{run: 'unterminated")
        with pytest.raises(ValueError, match="unparseable"):
            analyze_repo(repo)

    def test_non_dict_yaml_document_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        # a workflow file that's valid YAML but not a mapping (e.g. just a
        # string or list) shouldn't crash `.get("jobs")` on a non-dict.
        repo = tmp_path / "repo"
        _write_workflow(repo, "weird.yml", "just a bare string, not a mapping\n")
        result = analyze_repo(repo)
        assert result.has_ci_config is True
        assert result.any_workflow_runs_tests is False

    def test_multiple_workflow_files_counted(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_workflow(repo, "a.yml", "on: push\njobs:\n  x:\n    steps:\n      - run: npm test\n")
        _write_workflow(repo, "b.yaml", "on: push\njobs:\n  x:\n    steps:\n      - run: echo hi\n")
        result = analyze_repo(repo)
        assert result.workflow_count == 2
        assert result.any_workflow_runs_tests is True  # a.yml alone is enough


class TestRunCiGates:
    def test_writes_one_row_per_repo(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "a"
        repo_a.mkdir()
        repo_b = tmp_path / "b"
        _write_workflow(repo_b, "ci.yml", "on: push\njobs:\n  x:\n    steps:\n      - run: npm test\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_ci_gates([repo_a, repo_b], out_dir)
        assert len(out_path.read_text().splitlines()) == 3
