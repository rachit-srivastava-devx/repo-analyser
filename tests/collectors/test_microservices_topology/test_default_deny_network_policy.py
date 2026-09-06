from __future__ import annotations

from repo_analyser.collectors.microservices_topology.network_policy import (
    _is_default_deny_network_policy,
)


class TestDefaultDenyNetworkPolicy:
    def test_genuine_default_deny_all_ingress_and_egress(self) -> None:
        doc = {
            "kind": "NetworkPolicy",
            "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
        }
        assert _is_default_deny_network_policy(doc) is True

    def test_default_deny_ingress_only_with_no_explicit_policy_types(self) -> None:
        doc = {"kind": "NetworkPolicy", "spec": {"podSelector": {}}}
        assert _is_default_deny_network_policy(doc) is True

    def test_allow_all_policy_is_correctly_not_flagged_as_default_deny(self) -> None:
        doc = {
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {},
                "ingress": [{}],
                "egress": [{}],
                "policyTypes": ["Ingress", "Egress"],
            },
        }
        assert _is_default_deny_network_policy(doc) is False

    def test_scoped_pod_selector_is_not_default_deny(self) -> None:
        doc = {
            "kind": "NetworkPolicy",
            "spec": {"podSelector": {"matchLabels": {"app": "billing"}}, "policyTypes": ["Ingress"]},
        }
        assert _is_default_deny_network_policy(doc) is False

    def test_empty_ingress_list_is_equivalent_to_absent_key(self) -> None:
        doc = {
            "kind": "NetworkPolicy",
            "spec": {"podSelector": {}, "ingress": [], "policyTypes": ["Ingress"]},
        }
        assert _is_default_deny_network_policy(doc) is True

    def test_non_network_policy_kind_is_false(self) -> None:
        assert _is_default_deny_network_policy({"kind": "Deployment", "spec": {"podSelector": {}}}) is False

    def test_missing_pod_selector_is_false_not_a_crash(self) -> None:
        assert _is_default_deny_network_policy({"kind": "NetworkPolicy", "spec": {}}) is False

    def test_missing_spec_entirely_is_false_not_a_crash(self) -> None:
        assert _is_default_deny_network_policy({"kind": "NetworkPolicy"}) is False
