from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.api_contract import analyze_repo
from repo_analyser.collectors.api_contract.openapi_discovery import find_openapi_files

from ._api_contract_helpers import write


def test_malformed_yaml_reported_distinctly_not_a_crash(tmp_path: Path) -> None:
    write(tmp_path, "openapi.yaml", "openapi: [unterminated")
    r = analyze_repo(tmp_path)  # must not raise
    assert r.has_spec is False
    assert r.spec_parse_errors != ""
    assert "openapi.yaml" in r.spec_parse_errors


def test_malformed_json_reported_distinctly(tmp_path: Path) -> None:
    write(tmp_path, "openapi.json", "{not valid json")
    files, errors = find_openapi_files(tmp_path)
    assert files == []
    assert len(errors) == 1


def test_non_utf8_spec_content_reported_as_read_error_not_crash(tmp_path: Path) -> None:
    p = tmp_path / "openapi.yaml"
    p.write_bytes(b"openapi: 3.0.0\npaths: {}\ntitle: \xff\xfe bad bytes\n")
    r = analyze_repo(tmp_path)  # must not raise
    assert r.spec_parse_errors != "" or r.has_spec is False


def test_malformed_ci_workflow_does_not_crash_whole_run(tmp_path: Path) -> None:
    write(tmp_path, "openapi.yaml", "openapi: 3.0.0\npaths: {}\n")
    write(tmp_path, ".github/workflows/ci.yml", "jobs: \"not-a-mapping\"\n")
    r = analyze_repo(tmp_path)  # must not raise
    assert r.has_spec is True
    assert r.has_breaking_change_check is False


def test_huge_spec_file_still_parses(tmp_path: Path) -> None:
    lines = ["openapi: 3.0.0", "info: {title: t, version: '1.0'}", "paths:"]
    for i in range(2000):
        lines.append(f"  /path{i}:")
        lines.append(f"    get: {{summary: 'endpoint {i}', responses: {{'200': {{description: ok}}}}}}")
    write(tmp_path, "openapi.yaml", "\n".join(lines))
    r = analyze_repo(tmp_path)
    assert r.has_spec is True
    assert r.spec_kinds == "openapi"


def test_unicode_in_spec_content_handled(tmp_path: Path) -> None:
    write(
        tmp_path, "schema.graphql",
        'type Query { café: String @deprecated(reason: "日本語 sunset 2026-03-01") }',
    )
    r = analyze_repo(tmp_path)
    assert r.has_spec is True
    assert r.deprecated_with_sunset_count == 1
