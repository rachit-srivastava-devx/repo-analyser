from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.api_contract.deprecation import count_deprecations

from ._api_contract_helpers import OPENAPI_WITH_DEPRECATIONS, write


def test_no_deprecation_markers_distinct_from_no_spec(tmp_path: Path) -> None:
    p = write(tmp_path, "openapi.yaml", "openapi: 3.0.0\npaths: {}\n")
    assert count_deprecations(p, "openapi") == (0, 0)


def test_openapi_sunset_extension_key_counted(tmp_path: Path) -> None:
    p = write(tmp_path, "openapi.yaml", OPENAPI_WITH_DEPRECATIONS)
    with_sunset, without_sunset = count_deprecations(p, "openapi")
    assert with_sunset == 1
    assert without_sunset == 1


def test_graphql_deprecated_with_reason_date_counted(tmp_path: Path) -> None:
    p = write(tmp_path, "s.graphql", 'type Q { a: String @deprecated(reason: "sunset 2026-01-01") }')
    assert count_deprecations(p, "graphql") == (1, 0)


def test_graphql_deprecated_no_reason_counted_as_without_sunset(tmp_path: Path) -> None:
    p = write(tmp_path, "s.graphql", "type Q { a: String @deprecated }")
    assert count_deprecations(p, "graphql") == (0, 1)


def test_protobuf_deprecated_option_without_nearby_date(tmp_path: Path) -> None:
    p = write(tmp_path, "s.proto", 'message M { string old = 1 [deprecated = true]; }')
    assert count_deprecations(p, "protobuf") == (0, 1)


def test_protobuf_deprecated_with_nearby_comment_date(tmp_path: Path) -> None:
    p = write(tmp_path, "s.proto", "message M {\n  // sunset: 2026-01-01\n  string old = 1 [deprecated = true];\n}")
    assert count_deprecations(p, "protobuf") == (1, 0)


def test_unreadable_file_contributes_zero_not_a_crash(tmp_path: Path) -> None:
    p = tmp_path / "openapi.yaml"
    p.write_bytes(b"\xff\xfe not valid utf8")
    assert count_deprecations(p, "openapi") == (0, 0)


def test_adjacent_deprecated_fields_do_not_steal_each_others_sunset_date(tmp_path: Path) -> None:
    """Regression: a window search naively spanning SUNSET_WINDOW_LINES in
    both directions let a neighboring field's real sunset date get
    misattributed to a field with no sunset info of its own."""
    p = write(
        tmp_path, "s.graphql",
        'type User {\n'
        '  name: String @deprecated(reason: "use displayName, sunset 2026-06-01")\n'
        '  email: String @deprecated\n'
        "}\n",
    )
    assert count_deprecations(p, "graphql") == (1, 1)
