from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.monorepo_tooling.analyze import analyze_repo

from ._monorepo_tooling_helpers import TURBO_PIPELINE_SCHEMA, TURBO_TASKS_SCHEMA, write


def test_turbo_tasks_schema_detected(tmp_path: Path) -> None:
    write(tmp_path, "turbo.json", TURBO_TASKS_SCHEMA)

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_valid_json is True
    assert result.turbo_schema == "tasks"
    assert result.turbo_task_count == 2
    assert "turbo" in result.orchestrators_detected.split(";")


def test_turbo_legacy_pipeline_schema_detected(tmp_path: Path) -> None:
    write(tmp_path, "turbo.json", TURBO_PIPELINE_SCHEMA)

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_schema == "pipeline"
    assert result.turbo_task_count == 1


def test_turbo_bare_scaffold_no_tasks_or_pipeline_key(tmp_path: Path) -> None:
    write(tmp_path, "turbo.json", '{"$schema": "https://turbo.build/schema.json"}')

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_valid_json is True
    assert result.turbo_schema == ""
    assert result.turbo_task_count == 0


def test_turbo_malformed_json_reported_distinctly(tmp_path: Path) -> None:
    write(tmp_path, "turbo.json", "{ this is not json")

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_valid_json is False
    assert result.turbo_schema == ""
    assert "turbo.json" in result.config_parse_errors


def test_turbo_config_not_valid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "turbo.json"
    path.write_bytes(b"\xff\xfe not utf-8")

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_valid_json is False
    assert "turbo.json" in result.config_parse_errors


def test_turbo_json_top_level_is_not_an_object(tmp_path: Path) -> None:
    write(tmp_path, "turbo.json", '["a", "b"]')

    result = analyze_repo(tmp_path)

    assert result.turbo_present is True
    assert result.turbo_valid_json is False
    assert result.turbo_schema == ""


def test_turbo_and_nx_both_present_migration_scenario(tmp_path: Path) -> None:
    from ._monorepo_tooling_helpers import NX_CONFIGURED
    write(tmp_path, "nx.json", NX_CONFIGURED)
    write(tmp_path, "turbo.json", TURBO_TASKS_SCHEMA)

    result = analyze_repo(tmp_path)

    detected = set(result.orchestrators_detected.split(";"))
    assert detected == {"nx", "turbo"}
    assert result.orchestrator_count == 2
    assert result.nx_present is True
    assert result.turbo_present is True
