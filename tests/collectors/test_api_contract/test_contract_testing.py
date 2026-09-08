from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.api_contract.contract_testing import contract_test_tools_detected

from ._api_contract_helpers import workflow, write


def test_no_signals_reports_empty(tmp_path: Path) -> None:
    assert contract_test_tools_detected(tmp_path) == set()


def test_dependency_manifest_signal(tmp_path: Path) -> None:
    write(tmp_path, "package.json", '{"devDependencies": {"dredd": "^14.0.0"}}')
    assert contract_test_tools_detected(tmp_path) == {"dredd"}


def test_python_requirements_signal(tmp_path: Path) -> None:
    write(tmp_path, "requirements.txt", "schemathesis==3.20.0\n")
    assert contract_test_tools_detected(tmp_path) == {"schemathesis"}


def test_config_dir_signal(tmp_path: Path) -> None:
    write(tmp_path, "pacts/consumer-provider.json", "{}")
    assert contract_test_tools_detected(tmp_path) == {"pact"}


def test_ci_step_signal(tmp_path: Path) -> None:
    workflow(tmp_path, "ci.yml", """
on: [push]
jobs:
  build:
    steps:
      - run: schemathesis run --checks all openapi.yaml
""")
    assert contract_test_tools_detected(tmp_path) == {"schemathesis"}


def test_multiple_tools_all_reported(tmp_path: Path) -> None:
    write(tmp_path, "package.json", '{"dependencies": {"pact": "^11.0.0"}}')
    write(tmp_path, "pacts/x.json", "{}")
    assert contract_test_tools_detected(tmp_path) == {"pact"}


def test_malformed_package_json_does_not_crash(tmp_path: Path) -> None:
    write(tmp_path, "package.json", "{not valid json")
    assert contract_test_tools_detected(tmp_path) == set()


def test_package_json_not_a_dict_does_not_crash(tmp_path: Path) -> None:
    write(tmp_path, "package.json", "[1, 2, 3]")
    assert contract_test_tools_detected(tmp_path) == set()


def test_non_utf8_requirements_file_does_not_crash(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_bytes(b"\xff\xfe schemathesis\n")
    contract_test_tools_detected(tmp_path)  # must not raise
