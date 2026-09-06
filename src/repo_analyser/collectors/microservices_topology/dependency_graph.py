"""Signal (a): service count plus a docker-compose `depends_on`
dependency-cycle check (networkx.simple_cycles on a directed graph of
service->depends_on edges -- reuses the same library knowledge_graph.py
already depends on, same "build a graph, ask networkx a structural
question" shape). Deliberately scoped to docker-compose specifically,
matching the brief's own `services: {name: {depends_on: [...]}}` shape --
plain Kubernetes has no first-class "this workload depends on that one"
field to check the same way."""
from __future__ import annotations

from pathlib import Path

import networkx as nx

from .fs_helpers import _read_yaml_docs


def _compose_docs(repo: Path) -> list[dict]:
    """Root docker-compose.yml/.yaml only -- matches repo_type.py's own
    `_detect_microservices` root-only convention exactly."""
    docs: list[dict] = []
    for compose_name in ("docker-compose.yml", "docker-compose.yaml"):
        docs.extend(_read_yaml_docs(repo / compose_name))
    return docs


def _compose_services(docs: list[dict]) -> dict[str, dict]:
    services: dict[str, dict] = {}
    for doc in docs:
        svc = doc.get("services")
        if isinstance(svc, dict):
            for name, cfg in svc.items():
                services[name] = cfg if isinstance(cfg, dict) else {}
    return services


def _depends_on_targets(cfg: dict, known_services: set[str]) -> list[str]:
    """Compose supports both the short list form (`depends_on: [a, b]`) and
    the long form (`depends_on: {a: {condition: service_healthy}}`) --
    both are handled, since only checking one would silently miss real
    edges written the other way. A `depends_on` entry naming a service
    that was never actually declared (a real but malformed compose file)
    is dropped rather than added as a phantom graph node -- it can never
    be part of a real cycle among the services that do exist."""
    depends_on = cfg.get("depends_on")
    if isinstance(depends_on, dict):
        names = list(depends_on.keys())
    elif isinstance(depends_on, list):
        names = [d for d in depends_on if isinstance(d, str)]
    else:
        names = []
    return [n for n in names if n in known_services]


def _dependency_cycle(services: dict[str, dict]) -> tuple[bool, str]:
    """Directed graph of service -> depends_on edges; `nx.simple_cycles`
    reports a self-loop (a service that depends_on itself) as its own
    length-1 cycle, which this renders as "a -> a" rather than a bare "a"
    that would look like a formatting bug, not a real (if degenerate)
    cycle. Only the first cycle networkx reports is named in
    `cycle_detail` (there may be more than one independent cycle in a
    large service graph) -- `has_dependency_cycle` is still correctly True
    whenever any exist; naming every cycle is a real but separate
    enhancement, not attempted here rather than silently claimed."""
    graph: nx.DiGraph = nx.DiGraph()
    graph.add_nodes_from(services)
    for name, cfg in services.items():
        for target in _depends_on_targets(cfg, set(services)):
            graph.add_edge(name, target)
    cycles = list(nx.simple_cycles(graph))
    if not cycles:
        return False, ""
    cycle = cycles[0]
    return True, " -> ".join((*cycle, cycle[0]))
