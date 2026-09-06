"""Microservices topology and resilience-posture signals -- a DEEPER pass
than repo_type.py's own `_detect_microservices`, which only answers "is
this repo microservices-shaped at all" (Dockerfile/compose/service-mesh-CRD
*presence*, used to pick `primary_type`). This module assumes that's
already true and asks harder questions of the same manifest tree already
on disk: does the declared service graph have a dependency cycle, is a
service mesh with mTLS actually configured, is there a real default-deny
network policy, is progressive/canary rollout configured, and is a
resilience library (circuit breaker / retry) even a declared dependency.

No external tool -- pure docker-compose/k8s-manifest YAML parsing plus
package-manifest grep, the same "config presence, not live execution"
shape as performance.py/e2e_quality.py (see docs/ROADMAP.md's
microservices.md gap-analysis note: roughly 55 of 89 checklist criteria
for this archetype need a *running* cluster/mesh/broker this git-clone-
only tool has no access to -- everything here is deliberately the
static-analyzable remainder).

Consolidated by design (docs/ROADMAP.md, and the microservices.md
gap-analysis note above it): the research pass proposed ~12 separate
single-purpose collector names for this archetype (service_topology_audit,
resilience_pattern_audit, service_mesh_audit, network_policy_audit,
canary_rollout_audit, ...) that all reduce to "parse the same
docker-compose/k8s YAML tree, look for a different key" -- a
speculative-abstraction smell per AGENTS.md Sec 4. This is ONE collector:
one YAML-tree walk, five signal-detection functions, one row per repo.

Five signals, v1 scope -- split by concern across this package's
submodules, see each one's own docstring for the full per-signal
rationale: (a) dependency_graph.py, (b) service_mesh.py,
(c) network_policy.py, (d) canary_rollout.py, (e) resilience_libs.py.
The shared docker-compose/k8s YAML tree walk they all read from is
fs_helpers.py; analyze.py documents the skip_reason gate that combines
every signal into one result row.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import MicroservicesTopologyResult
from .runner import run_microservices_topology

__all__ = ["MicroservicesTopologyResult", "analyze_repo", "run_microservices_topology"]
