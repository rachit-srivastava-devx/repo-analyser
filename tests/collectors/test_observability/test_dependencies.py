from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.observability.dependencies import (
    all_declared_dependencies,
    detect_logging_libs,
    detect_metrics_libs,
    detect_tracing_libs,
)


class TestAllDeclaredDependencies:
    def test_merges_all_three_languages(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"winston": "^3.0.0"}}))
        (tmp_path / "requirements.txt").write_text("structlog==23.1.0\n")
        (tmp_path / "go.mod").write_text("module m\n\nrequire github.com/rs/zerolog v1.31.0\n")
        all_deps = all_declared_dependencies(tmp_path)
        assert {"winston", "structlog", "github.com/rs/zerolog"} <= all_deps

    def test_package_json_with_non_dict_dependencies_key_does_not_raise(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": ["winston"]}))
        assert all_declared_dependencies(tmp_path) == set()

    def test_no_manifests_at_all_returns_empty_set(self, tmp_path: Path) -> None:
        assert all_declared_dependencies(tmp_path) == set()


class TestDetectLibs:
    def test_logging_libs_matches_known_names_only(self) -> None:
        assert detect_logging_libs({"winston", "lodash"}) == {"winston"}
        assert detect_logging_libs({"github.com/rs/zerolog"}) == {"zerolog"}
        assert detect_logging_libs({"structlog"}) == {"structlog"}
        assert detect_logging_libs(set()) == set()

    def test_tracing_libs_are_separate_from_logging(self) -> None:
        assert detect_tracing_libs({"@opentelemetry/api"}) == {"opentelemetry"}
        assert detect_tracing_libs({"opentelemetry-api"}) == {"opentelemetry"}
        assert detect_tracing_libs({"go.opentelemetry.io/otel"}) == {"opentelemetry"}
        # winston is logging-only, never counted as tracing.
        assert detect_tracing_libs({"winston"}) == set()

    def test_metrics_libs(self) -> None:
        assert detect_metrics_libs({"prom-client"}) == {"prom-client"}
        assert detect_metrics_libs({"prometheus-client"}) == {"prometheus_client"}
        assert detect_metrics_libs({"github.com/prometheus/client_golang"}) == {"prometheus_client"}

    def test_multiple_logging_libs_detected_at_once_are_both_reported(self) -> None:
        # analyze.py joins these with ";" into one deterministic
        # (sorted) string -- the detection layer itself just returns the
        # full matched set, unordered.
        assert detect_logging_libs({"winston", "pino"}) == {"winston", "pino"}
