"""Data shapes and constants shared across microservices_topology's
submodules."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Sidecar auto-injection annotation key (Istio convention; Linkerd's own
# equivalent, `linkerd.io/inject`, is a real gap not covered in v1 -- name
# it here rather than silently missing it).
SIDECAR_INJECT_ANNOTATION = "sidecar.istio.io/inject"

# Flagger's `Canary` CRD, Argo Rollouts' `Rollout` CRD.
CANARY_ROLLOUT_CRD_KINDS = ("Canary", "Rollout")

RESILIENCE_LIBS_JS = ("opossum", "cockatiel")
RESILIENCE_LIBS_PYTHON = ("pybreaker", "tenacity")
RESILIENCE_LIBS_GO = ("sony/gobreaker", "avast/retry-go")

_PY_RESILIENCE_PATTERNS = {
    name: re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE) for name in RESILIENCE_LIBS_PYTHON
}


@dataclass
class MicroservicesTopologyResult:
    repo: str
    service_count: int
    has_dependency_cycle: bool
    cycle_detail: str
    has_service_mesh: bool
    mesh_kind: str
    has_network_policy_default_deny: bool
    has_canary_rollout_config: bool
    resilience_libs_detected: str
    skip_reason: str
