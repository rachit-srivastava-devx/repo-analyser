from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.monorepo_tooling.analyze import analyze_repo

from ._monorepo_tooling_helpers import NX_BARE_SCAFFOLD, NX_CONFIGURED, write


def test_nx_configured_graph_detected(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", NX_CONFIGURED)
    write(tmp_path, "apps/api/project.json", "{}")
    write(tmp_path, "libs/shared/project.json", "{}")

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is True
    assert result.nx_has_configured_graph is True
    assert result.nx_project_json_count == 2
    assert "nx" in result.orchestrators_detected.split(";")
    assert result.skip_reason == ""


def test_nx_bare_scaffold_is_present_but_unconfigured(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", NX_BARE_SCAFFOLD)

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is True
    assert result.nx_has_configured_graph is False


def test_nx_malformed_json_reported_distinctly(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", "{not valid json,,,")

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is False
    assert result.nx_has_configured_graph is False
    assert "nx.json" in result.config_parse_errors
    # A malformed-but-present config still counts as "detected" -- it is
    # not silently treated as "no Nx".
    assert "nx" in result.orchestrators_detected.split(";")


def test_nx_config_present_but_empty_file(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", "")

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is False
    assert result.config_parse_errors != ""


def test_nx_config_not_valid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "nx.json"
    path.write_bytes(b"\xff\xfe not utf-8")

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is False
    assert "nx.json" in result.config_parse_errors


def test_nx_json_top_level_is_not_an_object(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", "[1, 2, 3]")

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is False
    assert result.nx_has_configured_graph is False
