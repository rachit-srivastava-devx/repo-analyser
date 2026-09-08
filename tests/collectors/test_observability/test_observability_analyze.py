from __future__ import annotations

import json
from pathlib import Path

from _observability_helpers import write_files

from repo_analyser.collectors.observability.analyze import analyze_repo


class TestAnalyzeRepo:
    def test_empty_repo_reports_skip_reason_not_silent_empty(self, tmp_path: Path) -> None:
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is False
        assert result.has_metrics_lib is False
        assert result.has_tracing is False
        assert result.has_k8s_health_probes is False
        assert "no observability signal found" in result.skip_reason

    def test_js_repo_with_opentelemetry_and_prom_client(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"package.json": json.dumps({
            "dependencies": {"@opentelemetry/api": "^1.7.0", "prom-client": "^15.0.0"},
        })})
        result = analyze_repo(tmp_path)
        assert result.has_tracing is True
        assert result.tracing_lib == "opentelemetry"
        assert result.has_metrics_lib is True
        assert result.metrics_lib == "prom-client"
        assert result.has_structured_logging is False
        assert result.logging_lib == ""
        assert result.has_k8s_health_probes is False
        assert result.skip_reason == ""

    def test_python_repo_with_structlog_in_pyproject_toml(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "pyproject.toml": '[project]\nname = "svc"\ndependencies = [\n    "structlog>=23.1.0",\n]\n',
        })
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is True
        assert result.logging_lib == "structlog"
        assert result.has_metrics_lib is False
        assert result.has_tracing is False
        assert result.has_k8s_health_probes is False
        assert result.skip_reason == ""

    def test_repo_with_k8s_dir_and_readiness_probe(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "k8s/deployment.yaml": (
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "spec:\n"
                "  template:\n"
                "    spec:\n"
                "      containers:\n"
                "        - name: app\n"
                "          readinessProbe:\n"
                "            httpGet:\n"
                "              path: /health\n"
            ),
        })
        result = analyze_repo(tmp_path)
        assert result.has_k8s_health_probes is True
        assert result.skip_reason == ""

    def test_chart_yaml_alone_sets_k8s_health_probes(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"Chart.yaml": "apiVersion: v2\nname: my-service\nversion: 0.1.0\n"})
        result = analyze_repo(tmp_path)
        assert result.has_k8s_health_probes is True
        assert result.skip_reason == ""

    def test_go_repo_with_zerolog_and_client_golang(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "go.mod": (
                "module github.com/example/service\n\ngo 1.21\n\n"
                "require (\n"
                "\tgithub.com/rs/zerolog v1.31.0\n"
                "\tgithub.com/prometheus/client_golang v1.17.0\n"
                ")\n"
            ),
        })
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is True
        assert result.logging_lib == "zerolog"
        assert result.has_metrics_lib is True
        assert result.metrics_lib == "prometheus_client"
        assert result.has_tracing is False
        assert result.skip_reason == ""

    def test_only_one_of_the_signals_present(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"package.json": json.dumps({"dependencies": {"prom-client": "^15.0.0"}})})
        result = analyze_repo(tmp_path)
        assert result.has_metrics_lib is True
        assert result.has_structured_logging is False
        assert result.has_tracing is False
        assert result.has_k8s_health_probes is False
        assert result.skip_reason == ""

    def test_manifest_present_but_no_known_library_is_not_a_skip(self, tmp_path: Path) -> None:
        # a package.json exists (we had something to look at) but
        # declares none of the libraries this module recognizes -- must
        # be reported as a real "checked, found nothing" row, not
        # conflated with the "there was nothing to even check" skip case.
        write_files(tmp_path, {"package.json": json.dumps({"dependencies": {"lodash": "^4.0.0"}})})
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is False
        assert result.has_metrics_lib is False
        assert result.has_tracing is False
        assert result.has_k8s_health_probes is False
        assert result.skip_reason == ""

    def test_malformed_yaml_in_k8s_dir_does_not_raise_and_is_not_a_false_positive(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"k8s/broken.yaml": "livenessProbe: [unterminated\n"})
        result = analyze_repo(tmp_path)
        assert result.has_k8s_health_probes is False
        assert result.skip_reason == ""

    def test_malformed_package_json_degrades_to_no_js_signals(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"package.json": "{not valid json,,,"})
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is False
        assert result.has_tracing is False
        assert result.has_metrics_lib is False
        # package.json exists (even though unparseable), so this is a
        # real manifest we had -- not the "nothing at all" skip case.
        assert result.skip_reason == ""

    def test_multiple_logging_libs_reports_both_sorted_and_deterministic(self, tmp_path: Path) -> None:
        # when a repo declares more than one known logging library at
        # once, logging_lib reports all of them, ";"-joined in sorted
        # (alphabetical) order -- deterministic regardless of dict/set
        # iteration order, and never silently drops one.
        write_files(tmp_path, {"package.json": json.dumps({
            "dependencies": {"winston": "^3.0.0", "pino": "^8.0.0"},
        })})
        result = analyze_repo(tmp_path)
        assert result.has_structured_logging is True
        assert result.logging_lib == "pino;winston"
