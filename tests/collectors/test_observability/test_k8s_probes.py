from __future__ import annotations

from pathlib import Path

from _observability_helpers import write_files

from repo_analyser.collectors.observability.k8s_probes import (
    contains_health_probe_key,
    has_chart_yaml,
    yaml_docs,
)


class TestYamlDocs:
    def test_valid_single_doc(self) -> None:
        docs = yaml_docs("a: 1\nb: 2\n")
        assert docs == [{"a": 1, "b": 2}]

    def test_multi_document_yaml(self) -> None:
        docs = yaml_docs("a: 1\n---\nb: 2\n")
        assert docs == [{"a": 1}, {"b": 2}]

    def test_malformed_yaml_returns_empty_list_not_raise(self) -> None:
        # unterminated flow mapping -- a real YAMLError, not just an
        # unusual-but-valid document.
        assert yaml_docs("livenessProbe: [unterminated\n") == []

    def test_empty_file_returns_empty_list(self) -> None:
        assert yaml_docs("") == []


class TestContainsHealthProbeKey:
    def test_top_level_key(self) -> None:
        assert contains_health_probe_key({"readinessProbe": {}}) is True

    def test_deeply_nested_key(self) -> None:
        doc = {"spec": {"template": {"spec": {"containers": [{"name": "app", "livenessProbe": {"httpGet": {}}}]}}}}
        assert contains_health_probe_key(doc) is True

    def test_no_matching_key(self) -> None:
        assert contains_health_probe_key({"spec": {"replicas": 3}}) is False

    def test_non_dict_non_list_scalar(self) -> None:
        assert contains_health_probe_key("just a string") is False
        assert contains_health_probe_key(None) is False


class TestHasChartYaml:
    def test_no_chart_yaml(self, tmp_path: Path) -> None:
        assert has_chart_yaml(tmp_path) is False

    def test_chart_yaml_present(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"Chart.yaml": "apiVersion: v2\nname: my-service\nversion: 0.1.0\n"})
        assert has_chart_yaml(tmp_path) is True

    def test_chart_yaml_inside_vendored_dir_excluded(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "node_modules/some-pkg/Chart.yaml": "apiVersion: v2\nname: unrelated\nversion: 0.1.0\n",
        })
        assert has_chart_yaml(tmp_path) is False
