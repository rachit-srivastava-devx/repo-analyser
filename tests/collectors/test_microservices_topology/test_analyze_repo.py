from __future__ import annotations

from pathlib import Path

import yaml
from _microservices_topology_helpers import _write_compose

from repo_analyser.collectors.microservices_topology import analyze_repo


class TestAnalyzeRepo:
    def test_no_manifests_at_all_reports_skip_reason(self, tmp_path: Path) -> None:
        result = analyze_repo(tmp_path)
        assert result.skip_reason != ""
        assert result.service_count == 0
        assert result.has_dependency_cycle is False
        assert result.has_service_mesh is False
        assert result.has_network_policy_default_deny is False
        assert result.has_canary_rollout_config is False
        assert result.resilience_libs_detected == ""

    def test_docker_compose_three_services_no_cycle(self, tmp_path: Path) -> None:
        _write_compose(tmp_path, {
            "web": {"depends_on": ["api"]},
            "api": {"depends_on": ["db"]},
            "db": {},
        })
        result = analyze_repo(tmp_path)
        assert result.skip_reason == ""
        assert result.service_count == 3
        assert result.has_dependency_cycle is False
        assert result.cycle_detail == ""

    def test_docker_compose_genuine_cycle_names_actual_path(self, tmp_path: Path) -> None:
        _write_compose(tmp_path, {
            "a": {"depends_on": ["b"]},
            "b": {"depends_on": ["c"]},
            "c": {"depends_on": ["a"]},
        })
        result = analyze_repo(tmp_path)
        assert result.has_dependency_cycle is True
        nodes = result.cycle_detail.split(" -> ")
        assert nodes[0] == nodes[-1]
        assert set(nodes[:-1]) == {"a", "b", "c"}

    def test_docker_compose_with_zero_services_is_valid_empty_result(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("version: '3.8'\n")
        result = analyze_repo(tmp_path)
        assert result.skip_reason == ""
        assert result.service_count == 0
        assert result.has_dependency_cycle is False

    def test_malformed_docker_compose_yml_does_not_crash_and_skips(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("services: [this is: not, valid: yaml: at all}}}\n")
        result = analyze_repo(tmp_path)
        assert result.skip_reason != ""
        assert result.service_count == 0
        assert result.has_dependency_cycle is False

    def test_istio_virtualservice_yaml_detected_as_service_mesh(self, tmp_path: Path) -> None:
        (tmp_path / "virtualservice.yaml").write_text(yaml.safe_dump({
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {"name": "reviews-route"},
        }))
        result = analyze_repo(tmp_path)
        assert result.skip_reason == ""
        assert result.has_service_mesh is True
        assert result.mesh_kind == "VirtualService"

    def test_genuine_default_deny_network_policy_detected(self, tmp_path: Path) -> None:
        (tmp_path / "netpol.yaml").write_text(yaml.safe_dump({
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "default-deny-all"},
            "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
        }))
        result = analyze_repo(tmp_path)
        assert result.has_network_policy_default_deny is True

    def test_allow_all_network_policy_correctly_not_flagged(self, tmp_path: Path) -> None:
        (tmp_path / "netpol.yaml").write_text(yaml.safe_dump({
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "allow-all"},
            "spec": {
                "podSelector": {},
                "ingress": [{}],
                "egress": [{}],
                "policyTypes": ["Ingress", "Egress"],
            },
        }))
        result = analyze_repo(tmp_path)
        assert result.has_network_policy_default_deny is False
        assert result.skip_reason == ""

    def test_flagger_canary_crd_detected(self, tmp_path: Path) -> None:
        (tmp_path / "canary.yaml").write_text(yaml.safe_dump({
            "apiVersion": "flagger.app/v1beta1",
            "kind": "Canary",
            "metadata": {"name": "podinfo"},
        }))
        result = analyze_repo(tmp_path)
        assert result.has_canary_rollout_config is True

    def test_argo_rollout_crd_detected(self, tmp_path: Path) -> None:
        (tmp_path / "rollout.yaml").write_text(yaml.safe_dump({
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Rollout",
            "metadata": {"name": "podinfo"},
        }))
        result = analyze_repo(tmp_path)
        assert result.has_canary_rollout_config is True

    def test_pybreaker_in_requirements_detected_via_analyze_repo(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pybreaker==1.2.0\n")
        result = analyze_repo(tmp_path)
        assert result.skip_reason != ""
        assert result.resilience_libs_detected == ""

    def test_pybreaker_detected_alongside_a_real_manifest(self, tmp_path: Path) -> None:
        _write_compose(tmp_path, {"api": {}})
        (tmp_path / "requirements.txt").write_text("pybreaker==1.2.0\n")
        result = analyze_repo(tmp_path)
        assert result.skip_reason == ""
        assert result.resilience_libs_detected == "pybreaker"

    def test_multiple_resilience_libs_are_semicolon_joined_sorted(self, tmp_path: Path) -> None:
        _write_compose(tmp_path, {"api": {}})
        (tmp_path / "requirements.txt").write_text("tenacity==8.2\npybreaker==1.2.0\n")
        result = analyze_repo(tmp_path)
        assert result.resilience_libs_detected == "pybreaker;tenacity"
