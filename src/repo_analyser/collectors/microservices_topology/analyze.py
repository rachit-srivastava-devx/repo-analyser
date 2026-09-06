"""Per-repo orchestration: combines the five topology/resilience signals
computed across this package's submodules into one result row.

skip_reason fires only when the repo has no docker-compose file that
parses into at least one YAML document, AND no other `.yaml`/`.yml` file
anywhere in the tree parses into a document with a non-empty `kind`
field -- i.e. nothing resembling a compose or k8s manifest exists to
analyze at all. A compose/k8s file that exists on disk but fails to parse
(malformed YAML) contributes no usable document either way, so it is
indistinguishable from "absent" for this gate -- the same
silent-skip-on-parse-error behavior repo_type.py's own `_read_yaml_docs`
and performance.py's `_load_workflow_docs` already use tree-wide; not a
new gap introduced here (see docs/ROADMAP.md's own build-out notes and
AGENTS.md Sec 6's "silent empty result" row -- the distinction that
matters is genuinely-absent vs genuinely-found-nothing, which this module
preserves; malformed-vs-absent is not a distinction this codebase's
YAML-reading convention has ever surfaced as a separate column, so this
does not invent one either). A compose file that DOES parse but declares
zero services is a normal, valid empty result (service_count=0), not a
skip.
"""
from __future__ import annotations

from pathlib import Path

from .canary_rollout import _has_canary_rollout_config
from .dependency_graph import _compose_docs, _compose_services, _dependency_cycle
from .fs_helpers import _collect_yaml_tree
from .models import MicroservicesTopologyResult
from .network_policy import _has_network_policy_default_deny
from .resilience_libs import _resilience_libs_detected
from .service_mesh import _service_mesh_signals


def analyze_repo(repo: Path) -> MicroservicesTopologyResult:
    compose_docs = _compose_docs(repo)
    services = _compose_services(compose_docs)
    k8s_docs, yaml_text = _collect_yaml_tree(repo)

    has_any_manifest = bool(compose_docs) or any(
        isinstance(d.get("kind"), str) and d.get("kind") for d in k8s_docs
    )
    if not has_any_manifest:
        return MicroservicesTopologyResult(
            repo=repo.name, service_count=0, has_dependency_cycle=False, cycle_detail="",
            has_service_mesh=False, mesh_kind="", has_network_policy_default_deny=False,
            has_canary_rollout_config=False, resilience_libs_detected="",
            skip_reason="no docker-compose file or k8s-manifest-shaped YAML doc "
                        "(non-empty 'kind' field) found anywhere in the repo",
        )

    has_cycle, cycle_detail = _dependency_cycle(services)
    mesh_labels = _service_mesh_signals(k8s_docs, yaml_text)
    resilience_libs = _resilience_libs_detected(repo)

    return MicroservicesTopologyResult(
        repo=repo.name,
        service_count=len(services),
        has_dependency_cycle=has_cycle,
        cycle_detail=cycle_detail,
        has_service_mesh=bool(mesh_labels),
        mesh_kind=";".join(sorted(mesh_labels)),
        has_network_policy_default_deny=_has_network_policy_default_deny(k8s_docs),
        has_canary_rollout_config=_has_canary_rollout_config(k8s_docs),
        resilience_libs_detected=";".join(sorted(resilience_libs)),
        skip_reason="",
    )
