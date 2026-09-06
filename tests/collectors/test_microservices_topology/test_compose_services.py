from __future__ import annotations

from repo_analyser.collectors.microservices_topology.dependency_graph import _compose_services


class TestComposeServices:
    def test_missing_services_key_is_zero_services(self) -> None:
        assert _compose_services([{"version": "3.8"}]) == {}

    def test_merges_across_multiple_docs(self) -> None:
        docs = [{"services": {"a": {}}}, {"services": {"b": {}}}]
        assert _compose_services(docs) == {"a": {}, "b": {}}

    def test_non_dict_service_config_becomes_empty_dict(self) -> None:
        assert _compose_services([{"services": {"a": None}}]) == {"a": {}}
