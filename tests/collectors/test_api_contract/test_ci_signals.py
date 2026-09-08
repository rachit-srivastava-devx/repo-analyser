from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.api_contract.ci_signals import breaking_change_tools_wired_into_ci
from repo_analyser.collectors.api_contract.ci_workflows import load_workflow_docs, step_texts

from ._api_contract_helpers import workflow


def test_no_workflows_dir_reports_no_check(tmp_path: Path) -> None:
    tools, errors = breaking_change_tools_wired_into_ci(tmp_path)
    assert tools == set()
    assert errors == []


def test_real_oasdiff_invocation_detected(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", """
on: [pull_request]
jobs:
  build:
    steps:
      - run: oasdiff breaking old.yaml new.yaml
""")
    tools, _ = breaking_change_tools_wired_into_ci(tmp_path)
    assert tools == {"oasdiff"}


def test_bare_mention_in_comment_not_a_command_is_not_counted(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", """
on: [pull_request]
jobs:
  build:
    steps:
      - run: |
          # we should really run oasdiff breaking here someday
          echo done
""")
    tools, _ = breaking_change_tools_wired_into_ci(tmp_path)
    assert tools == set()


def test_buf_breaking_word_boundary_not_confused_with_buf_lint(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", """
on: [push]
jobs:
  build:
    steps:
      - run: buf lint
""")
    tools, _ = breaking_change_tools_wired_into_ci(tmp_path)
    assert tools == set()


def test_graphql_inspector_name_only_match(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", """
on: [pull_request]
jobs:
  build:
    steps:
      - run: npx graphql-inspector diff old.graphql new.graphql
""")
    tools, _ = breaking_change_tools_wired_into_ci(tmp_path)
    assert tools == {"graphql-inspector"}


def test_unparseable_workflow_yaml_reported_as_error_not_crash(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", "on: [push\njobs: {")
    docs, errors = load_workflow_docs(tmp_path)
    assert docs == []
    assert len(errors) == 1
    assert "ci.yml" in errors[0]


def test_step_texts_non_dict_job_skipped(tmp_path: Path) -> None:
    doc = {"jobs": {"build": "not-a-dict"}}
    assert step_texts(doc) == []


def test_step_texts_non_list_steps_skipped(tmp_path: Path) -> None:
    doc = {"jobs": {"build": {"steps": "not-a-list"}}}
    assert step_texts(doc) == []
