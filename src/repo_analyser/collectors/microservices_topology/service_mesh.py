"""Signal (b): service-mesh/mTLS presence -- an Istio/Linkerd CRD `kind`
anywhere in the tree (repo_type.SERVICE_MESH_CRD_KINDS -- imported, not
redefined, since that module exports it as a public module-level constant
for exactly this reuse) or a `sidecar.istio.io/inject` annotation grepped
from raw YAML text."""
from __future__ import annotations

from ..repo_type import SERVICE_MESH_CRD_KINDS
from .models import SIDECAR_INJECT_ANNOTATION


def _service_mesh_signals(k8s_docs: list[dict], yaml_text: str) -> set[str]:
    labels = {doc["kind"] for doc in k8s_docs if doc.get("kind") in SERVICE_MESH_CRD_KINDS}
    if SIDECAR_INJECT_ANNOTATION in yaml_text:
        labels.add("sidecar-injection-annotation")
    return labels
