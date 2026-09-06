from __future__ import annotations

from repo_analyser.collectors.microservices_topology.dependency_graph import _dependency_cycle


class TestDependencyCycle:
    def test_no_services_no_cycle(self) -> None:
        assert _dependency_cycle({}) == (False, "")

    def test_three_services_no_cycle(self) -> None:
        services = {
            "web": {"depends_on": ["api"]},
            "api": {"depends_on": ["db"]},
            "db": {},
        }
        assert _dependency_cycle(services) == (False, "")

    def test_genuine_a_b_c_a_cycle_names_real_path(self) -> None:
        services = {
            "a": {"depends_on": ["b"]},
            "b": {"depends_on": ["c"]},
            "c": {"depends_on": ["a"]},
        }
        has_cycle, detail = _dependency_cycle(services)
        assert has_cycle is True
        assert " -> " in detail
        nodes = detail.split(" -> ")
        assert nodes[0] == nodes[-1]
        assert set(nodes[:-1]) == {"a", "b", "c"}

    def test_long_form_depends_on_dict_syntax_detects_same_cycle(self) -> None:
        services = {
            "a": {"depends_on": {"b": {"condition": "service_healthy"}}},
            "b": {"depends_on": {"a": {"condition": "service_started"}}},
        }
        has_cycle, detail = _dependency_cycle(services)
        assert has_cycle is True
        nodes = detail.split(" -> ")
        assert set(nodes[:-1]) == {"a", "b"}

    def test_self_referencing_single_service_cycle_of_length_one(self) -> None:
        services = {"a": {"depends_on": ["a"]}}
        has_cycle, detail = _dependency_cycle(services)
        assert has_cycle is True
        assert detail == "a -> a"

    def test_depends_on_naming_undeclared_service_is_ignored_not_a_phantom_node(self) -> None:
        services = {"a": {"depends_on": ["ghost"]}}
        assert _dependency_cycle(services) == (False, "")
