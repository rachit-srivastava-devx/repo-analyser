from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.api_contract import analyze_repo
from repo_analyser.collectors.api_contract.discovery import find_graphql_and_protobuf_files
from repo_analyser.collectors.api_contract.openapi_discovery import find_openapi_files

from ._api_contract_helpers import OPENAPI_MIN, write


def test_empty_repo_reports_zero_found_not_error(tmp_path: Path) -> None:
    r = analyze_repo(tmp_path)
    assert r.has_spec is False
    assert r.spec_kinds == ""
    assert r.spec_file_count == 0
    assert r.skip_reason != ""


def test_conventional_openapi_path_detected(tmp_path: Path) -> None:
    write(tmp_path, "docs/openapi.yaml", OPENAPI_MIN)
    files, errors = find_openapi_files(tmp_path)
    assert [f.name for f in files] == ["openapi.yaml"]
    assert errors == []


def test_unconventional_name_still_detected_via_content_check(tmp_path: Path) -> None:
    write(tmp_path, "specs/my-service.openapi.v2.yaml", OPENAPI_MIN)
    files, _ = find_openapi_files(tmp_path)
    assert len(files) == 1


def test_yaml_file_merely_named_openapi_but_not_a_schema_is_not_counted(tmp_path: Path) -> None:
    write(tmp_path, "openapi.yaml", "just: some\nunrelated: yaml\n")
    files, errors = find_openapi_files(tmp_path)
    assert files == []
    assert errors == []


def test_graphql_schema_file_detected_anywhere(tmp_path: Path) -> None:
    write(tmp_path, "src/gql/schema.graphql", "type Query { hello: String }")
    graphql, protobuf = find_graphql_and_protobuf_files(tmp_path)
    assert len(graphql) == 1
    assert protobuf == []


def test_protobuf_file_detected_anywhere(tmp_path: Path) -> None:
    write(tmp_path, "proto/svc.proto", "syntax = \"proto3\";")
    graphql, protobuf = find_graphql_and_protobuf_files(tmp_path)
    assert graphql == []
    assert len(protobuf) == 1


def test_protobuf_only_repo_detected_via_analyze_repo(tmp_path: Path) -> None:
    write(tmp_path, "proto/svc.proto", "syntax = \"proto3\";")
    r = analyze_repo(tmp_path)
    assert r.spec_kinds == "protobuf"
    assert r.has_spec is True


def test_multiple_kinds_at_once_all_reported(tmp_path: Path) -> None:
    write(tmp_path, "openapi.yaml", OPENAPI_MIN)
    write(tmp_path, "schema.graphql", "type Query { hello: String }")
    r = analyze_repo(tmp_path)
    assert r.spec_kinds == "openapi;graphql"
    assert r.spec_file_count == 2


def test_duplicate_spec_files_both_counted_same_kind_once(tmp_path: Path) -> None:
    write(tmp_path, "openapi.yaml", OPENAPI_MIN)
    write(tmp_path, "openapi.json", '{"openapi": "3.0.0", "info": {}, "paths": {}}')
    r = analyze_repo(tmp_path)
    assert r.spec_kinds == "openapi"
    assert r.spec_file_count == 2


def test_excluded_dirs_not_walked(tmp_path: Path) -> None:
    write(tmp_path, "node_modules/pkg/schema.graphql", "type Query { hello: String }")
    graphql, _ = find_graphql_and_protobuf_files(tmp_path)
    assert graphql == []


def test_gitignored_but_present_spec_file_still_counts(tmp_path: Path) -> None:
    """Deliberate, documented choice (see discovery.py's module docstring):
    this collector walks the real filesystem, not `git ls-files`."""
    write(tmp_path, ".gitignore", "openapi.yaml\n")
    write(tmp_path, "openapi.yaml", OPENAPI_MIN)
    r = analyze_repo(tmp_path)
    assert r.has_spec is True
