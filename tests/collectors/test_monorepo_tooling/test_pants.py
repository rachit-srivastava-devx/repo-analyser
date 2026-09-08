from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.monorepo_tooling.analyze import analyze_repo

from ._monorepo_tooling_helpers import PANTS_CONFIGURED, write


def test_pants_configured_backend_detected(tmp_path: Path) -> None:
    write(tmp_path, "pants.toml", PANTS_CONFIGURED)

    result = analyze_repo(tmp_path)

    assert result.pants_present is True
    assert result.pants_valid_toml is True
    assert result.pants_has_backend_section is True
    assert "pants" in result.orchestrators_detected.split(";")


def test_pants_bare_stub_no_backend_section(tmp_path: Path) -> None:
    write(tmp_path, "pants.toml", "[other]\nkey = \"value\"\n")

    result = analyze_repo(tmp_path)

    assert result.pants_present is True
    assert result.pants_valid_toml is True
    assert result.pants_has_backend_section is False


def test_pants_config_present_but_empty_file(tmp_path: Path) -> None:
    write(tmp_path, "pants.toml", "")

    result = analyze_repo(tmp_path)

    assert result.pants_present is True
    assert result.pants_valid_toml is True
    assert result.pants_has_backend_section is False
    assert result.config_parse_errors == ""


def test_pants_malformed_toml_reported_distinctly(tmp_path: Path) -> None:
    write(tmp_path, "pants.toml", "\x00\x01 not toml at all, no headers, no keys\x02")

    result = analyze_repo(tmp_path)

    assert result.pants_present is True
    assert result.pants_valid_toml is False
    assert "pants.toml" in result.config_parse_errors


def test_pants_config_not_valid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "pants.toml"
    path.write_bytes(b"\xff\xfe not utf-8")

    result = analyze_repo(tmp_path)

    assert result.pants_present is True
    assert result.pants_valid_toml is False
    assert "pants.toml" in result.config_parse_errors
