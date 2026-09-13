from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyser.collectors.ci_gates import (
    _lockfile_managers_found,
    _lockfiles_found,
    _package_json_precommit_signal,
    _precommit_signals,
    _workflow_is_deploy_only,
    _workflow_runs_tests,
    _workflow_verified_lockfile_managers,
    _workflow_verifies_lockfile,
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

    def test_pytest_run_step(self) -> None:
        # regression: this repo's own ci.yml ("pytest --cov=...") was
        # misclassified as not running tests until this pattern was added --
        # the pattern list previously covered JS/TS test runners only.
        doc = {"jobs": {"test": {"steps": [
            {"run": "pytest --cov=repo_analyser --cov-report=term-missing --cov-report=xml"},
        ]}}}
        assert _workflow_runs_tests(doc) is True

    def test_go_test_run_step(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "go test ./..."}]}}}
        assert _workflow_runs_tests(doc) is True

    def test_unittest_run_step(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "python -m unittest discover"}]}}}
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


class TestWorkflowVerifiesLockfile:
    def test_npm_ci_step(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "npm ci"}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_npm_install_is_not_verification(self) -> None:
        # npm install silently rewrites the lockfile on drift instead of
        # failing the build -- it must NOT count as enforcement.
        doc = {"jobs": {"build": {"steps": [{"run": "npm install"}]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_poetry_check(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "poetry check"}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_cargo_build_locked(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "cargo build --locked"}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_cargo_test_locked_with_extra_flags(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "cargo test --locked --all-features"}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_cargo_build_without_locked_is_not_verification(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "cargo build --release"}]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_go_mod_verify(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "go mod verify"}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_no_verification_signal_is_false(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "echo hello"}]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_npm_ci_mentioned_only_in_a_comment_is_not_verification(self) -> None:
        # A `run:` block is a literal shell script and can contain a bash
        # comment that merely mentions "npm ci" without invoking it -- the
        # actually-invoked command here is plain `npm install`, which must
        # not be shadowed by a substring match against the comment text.
        doc = {"jobs": {"build": {"steps": [{"run": (
            "# note: prod CI uses npm ci, but this workflow is dev-only\n"
            "npm install\n"
        )}]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_npm_ci_as_real_step_alongside_an_unrelated_comment(self) -> None:
        # A comment elsewhere in the same run block must not suppress a
        # genuine invocation later in the same script.
        doc = {"jobs": {"build": {"steps": [{"run": (
            "# installing dependencies\n"
            "npm ci\n"
        )}]}}}
        assert _workflow_verifies_lockfile(doc) is True

    def test_npm_ci_mentioned_only_inside_an_echoed_string_is_not_verification(self) -> None:
        # Defect: a bare substring search matches "npm ci" inside an
        # `echo "..."` string just as readily as a real invocation. The only
        # REAL install step here is the loose, unenforced `npm install` --
        # this must report False, not True.
        doc = {"jobs": {"build": {"steps": [
            {"run": 'echo "we should switch to npm ci"'},
            {"run": "npm install"},
        ]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_npm_ci_mentioned_only_inside_an_echoed_string_with_no_install_step_at_all(self) -> None:
        # Same false-positive shape, but with no install step of any kind
        # anywhere in the workflow -- nothing was invoked at all.
        doc = {"jobs": {"build": {"steps": [
            {"run": 'echo "we should switch to npm ci one day"'},
        ]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_npm_ci_in_single_quoted_echo_string_is_also_not_verification(self) -> None:
        doc = {"jobs": {"build": {"steps": [
            {"run": "echo 'reminder: prod uses npm ci'"},
            {"run": "npm install"},
        ]}}}
        assert _workflow_verifies_lockfile(doc) is False

    def test_real_npm_ci_step_alongside_an_unrelated_echo_string_still_verifies(self) -> None:
        # An echoed string elsewhere in the same script must not suppress a
        # genuine invocation later in the same run block.
        doc = {"jobs": {"build": {"steps": [
            {"run": 'echo "installing dependencies now"'},
            {"run": "npm ci"},
        ]}}}
        assert _workflow_verifies_lockfile(doc) is True


class TestWorkflowVerifiedLockfileManagers:
    def test_npm_ci_attributes_to_npm_only(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "npm ci"}]}}}
        assert _workflow_verified_lockfile_managers(doc) == {"npm"}

    def test_poetry_check_attributes_to_poetry_only(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "poetry check"}]}}}
        assert _workflow_verified_lockfile_managers(doc) == {"poetry"}

    def test_no_verification_signal_is_empty_set(self) -> None:
        doc = {"jobs": {"build": {"steps": [{"run": "npm install"}]}}}
        assert _workflow_verified_lockfile_managers(doc) == set()

    def test_echoed_npm_ci_string_does_not_attribute_to_npm(self) -> None:
        # Same defect-1 false-positive shape, checked at the per-manager
        # attribution function used for defect 2's fix.
        doc = {"jobs": {"build": {"steps": [
            {"run": 'echo "we should switch to npm ci"'},
            {"run": "npm install"},
        ]}}}
        assert _workflow_verified_lockfile_managers(doc) == set()

    def test_multiple_managers_verified_in_one_workflow(self) -> None:
        doc = {"jobs": {
            "node": {"steps": [{"run": "npm ci"}]},
            "python": {"steps": [{"run": "poetry check"}]},
        }}
        assert _workflow_verified_lockfile_managers(doc) == {"npm", "poetry"}


class TestLockfileManagersFound:
    def test_npm_lockfile_maps_to_npm(self) -> None:
        assert _lockfile_managers_found(["package-lock.json"]) == ["npm"]

    def test_poetry_lockfile_maps_to_poetry(self) -> None:
        assert _lockfile_managers_found(["poetry.lock"]) == ["poetry"]

    def test_no_lockfiles_is_empty(self) -> None:
        assert _lockfile_managers_found([]) == []

    def test_monorepo_subdirectory_paths_map_correctly(self) -> None:
        assert _lockfile_managers_found(
            ["services/api/poetry.lock", "services/web/package-lock.json"],
        ) == ["npm", "poetry"]

    def test_duplicate_manager_from_two_files_deduplicated(self) -> None:
        assert _lockfile_managers_found(
            ["packages/a/package-lock.json", "packages/b/package-lock.json"],
        ) == ["npm"]


class TestPrecommitSignals:
    def test_precommit_config_file_present(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".pre-commit-config.yaml").write_text("repos: []\n")
        assert _precommit_signals(repo) == [".pre-commit-config.yaml"]

    def test_precommit_config_present_but_empty_or_malformed_still_counts(self, tmp_path: Path) -> None:
        # This is a presence check, not a validity check -- an empty or
        # malformed .pre-commit-config.yaml still means a repo *intends* to
        # gate on pre-commit (and the file is never parsed as YAML here at
        # all, so malformed content can't raise).
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".pre-commit-config.yaml").write_text("")
        assert _precommit_signals(repo) == [".pre-commit-config.yaml"]
        (repo / ".pre-commit-config.yaml").write_text("not: valid: yaml: [structure")
        assert _precommit_signals(repo) == [".pre-commit-config.yaml"]

    def test_husky_dir_present(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / ".husky").mkdir(parents=True)
        assert _precommit_signals(repo) == [".husky"]

    def test_package_json_lint_staged_key(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text('{"name": "x", "lint-staged": {"*.js": "eslint"}}')
        assert _precommit_signals(repo) == ["package.json:lint-staged"]

    def test_package_json_pre_commit_key(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text('{"pre-commit": ["test"]}')
        assert _precommit_signals(repo) == ["package.json:pre-commit"]

    def test_no_signals_at_all(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        assert _precommit_signals(repo) == []

    def test_package_json_without_relevant_keys_is_no_signal(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text('{"name": "x", "scripts": {"test": "jest"}}')
        assert _package_json_precommit_signal(repo) is None

    def test_malformed_package_json_does_not_crash_and_contributes_no_signal(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{not valid json")
        assert _package_json_precommit_signal(repo) is None
        assert _precommit_signals(repo) == []

    def test_multiple_signals_all_reported_sorted(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / ".husky").mkdir(parents=True)
        (repo / ".pre-commit-config.yaml").write_text("repos: []\n")
        assert _precommit_signals(repo) == [".husky", ".pre-commit-config.yaml"]


class TestLockfilesFound:
    def test_single_lockfile(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        assert _lockfiles_found(repo) == ["package-lock.json"]

    def test_no_lockfile(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        assert _lockfiles_found(repo) == []

    def test_multiple_lockfiles_simultaneously_all_reported(self, tmp_path: Path) -> None:
        # A real, if unusual, repo state (e.g. mid-migration between package
        # managers) -- must not silently collapse to just one name.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        (repo / "yarn.lock").write_text("")
        assert _lockfiles_found(repo) == ["package-lock.json", "yarn.lock"]

    def test_monorepo_lockfiles_in_subdirectories_are_found(self, tmp_path: Path) -> None:
        # A monorepo commonly has no root lockfile at all -- each
        # per-package subdirectory manages its own. Root-empty must not be
        # reported as "no lockfile discipline" when subdirectories clearly
        # have it.
        repo = tmp_path / "repo"
        (repo / "packages" / "api").mkdir(parents=True)
        (repo / "packages" / "web").mkdir(parents=True)
        (repo / "packages" / "api" / "package-lock.json").write_text("{}")
        (repo / "packages" / "web" / "yarn.lock").write_text("")
        assert _lockfiles_found(repo) == [
            "packages/api/package-lock.json", "packages/web/yarn.lock",
        ]

    def test_lockfile_inside_node_modules_is_excluded(self, tmp_path: Path) -> None:
        # A transitive dependency can ship its own lockfile inside
        # node_modules -- that's not this repo's own lockfile discipline
        # and must not be counted.
        repo = tmp_path / "repo"
        (repo / "node_modules" / "some-dep").mkdir(parents=True)
        (repo / "node_modules" / "some-dep" / "package-lock.json").write_text("{}")
        assert _lockfiles_found(repo) == []


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

    def test_repo_with_precommit_config(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".pre-commit-config.yaml").write_text("repos: []\n")
        result = analyze_repo(repo)
        assert result.has_precommit_hook is True
        assert result.precommit_signals == ".pre-commit-config.yaml"

    def test_repo_with_no_precommit_signals(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = analyze_repo(repo)
        assert result.has_precommit_hook is False
        assert result.precommit_signals == ""

    def test_lockfile_present_but_ci_runs_plain_npm_install(self, tmp_path: Path) -> None:
        # lockfile committed, but CI never enforces it -- present and NOT
        # verified must both be visible, not collapsed into one flag.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        _write_workflow(repo, "ci.yml",
                         "on: push\njobs:\n  build:\n    steps:\n"
                         "      - run: npm install\n      - run: npm test\n")
        result = analyze_repo(repo)
        assert result.lockfile_present is True
        assert result.lockfiles_found == "package-lock.json"
        assert result.lockfile_managers_found == "npm"
        assert result.lockfile_managers_verified_in_ci == ""
        assert result.lockfile_verified_in_ci is False

    def test_lockfile_present_and_ci_runs_npm_ci(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        _write_workflow(repo, "ci.yml",
                         "on: push\njobs:\n  build:\n    steps:\n"
                         "      - run: npm ci\n      - run: npm test\n")
        result = analyze_repo(repo)
        assert result.lockfile_present is True
        assert result.lockfile_managers_verified_in_ci == "npm"
        assert result.lockfile_verified_in_ci is True

    def test_lockfile_mentioned_only_in_echo_is_not_verified(self, tmp_path: Path) -> None:
        # End-to-end regression for defect 1 through analyze_repo: the only
        # real install step is the loose `npm install`, so this repo's npm
        # lockfile must be reported present-but-not-verified.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        _write_workflow(repo, "ci.yml",
                         "on: push\njobs:\n  build:\n    steps:\n"
                         "      - run: echo \"we should switch to npm ci\"\n"
                         "      - run: npm install\n")
        result = analyze_repo(repo)
        assert result.lockfile_managers_found == "npm"
        assert result.lockfile_managers_verified_in_ci == ""
        assert result.lockfile_verified_in_ci is False

    def test_precommit_and_lockfile_computed_even_with_no_workflows_dir(self, tmp_path: Path) -> None:
        # Regression guard: precommit/lockfile signals must not depend on
        # .github/workflows existing -- a repo can gate locally via hooks
        # and have a committed lockfile with zero GitHub Actions workflows,
        # and the early-return path for "no workflows dir" must not blank
        # out these otherwise-independent columns.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".husky").mkdir()
        (repo / "yarn.lock").write_text("")
        result = analyze_repo(repo)
        assert result.has_ci_config is False
        assert result.has_precommit_hook is True
        assert result.precommit_signals == ".husky"
        assert result.lockfile_present is True
        assert result.lockfiles_found == "yarn.lock"
        # yarn has no wired-up enforcement pattern (disclosed gap, see the
        # module docstring) -- "found" but never "verified" is the correct,
        # honest result, not a guess.
        assert result.lockfile_managers_found == "yarn"
        assert result.lockfile_managers_verified_in_ci == ""
        assert result.lockfile_verified_in_ci is False

    def test_monorepo_mixed_compliance_attributed_per_manager(self, tmp_path: Path) -> None:
        # Defect 2's exact regression fixture: a monorepo with
        # services/api/poetry.lock (CI only runs the loose `poetry install`,
        # never `poetry check`) alongside services/web/package-lock.json (CI
        # correctly runs `npm ci`). Before the fix this collapsed to one
        # repo-wide `lockfile_verified_in_ci=True`, hiding that the poetry
        # side is unenforced. After the fix, npm and poetry must be
        # distinguishable: npm verified, poetry not.
        repo = tmp_path / "repo"
        (repo / "services" / "api").mkdir(parents=True)
        (repo / "services" / "web").mkdir(parents=True)
        (repo / "services" / "api" / "poetry.lock").write_text("")
        (repo / "services" / "web" / "package-lock.json").write_text("{}")
        _write_workflow(repo, "ci.yml", """
on: push
jobs:
  api:
    steps:
      - run: cd services/api && poetry install
      - run: pytest
  web:
    steps:
      - run: cd services/web && npm ci
      - run: npm test
""")
        result = analyze_repo(repo)
        assert result.lockfiles_found == "services/api/poetry.lock;services/web/package-lock.json"
        assert result.lockfile_managers_found == "npm;poetry"
        verified = set(result.lockfile_managers_verified_in_ci.split(";"))
        assert "npm" in verified
        assert "poetry" not in verified
        assert result.lockfile_managers_verified_in_ci == "npm"

    def test_monorepo_mixed_compliance_aggregate_and_breakdown_coexist(self, tmp_path: Path) -> None:
        # Same monorepo fixture as
        # test_monorepo_mixed_compliance_attributed_per_manager (npm side
        # enforced via `npm ci`, poetry side only `poetry install`, never
        # `poetry check`) -- this test's job is specifically to prove the
        # restored derived aggregate (lockfile_verified_in_ci) and the
        # authoritative per-manager breakdown
        # (lockfile_managers_verified_in_ci) tell two different, both-true
        # parts of the story without contradicting each other: the
        # repo-wide aggregate is True (at least one manager -- npm -- is
        # verified), while the breakdown correctly still shows only "npm",
        # not "npm;poetry". Reading the aggregate alone as "every manager is
        # compliant" would be exactly the conflation bug this module's fix
        # exists to prevent.
        repo = tmp_path / "repo"
        (repo / "services" / "api").mkdir(parents=True)
        (repo / "services" / "web").mkdir(parents=True)
        (repo / "services" / "api" / "poetry.lock").write_text("")
        (repo / "services" / "web" / "package-lock.json").write_text("{}")
        _write_workflow(repo, "ci.yml", """
on: push
jobs:
  api:
    steps:
      - run: cd services/api && poetry install
      - run: pytest
  web:
    steps:
      - run: cd services/web && npm ci
      - run: npm test
""")
        result = analyze_repo(repo)
        assert result.lockfile_verified_in_ci is True
        assert result.lockfile_managers_verified_in_ci == "npm"

    def test_multiple_lockfiles_via_analyze_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        (repo / "yarn.lock").write_text("")
        result = analyze_repo(repo)
        assert result.lockfile_present is True
        assert result.lockfiles_found == "package-lock.json;yarn.lock"


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
