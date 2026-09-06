"""Signal (d): canary/progressive-rollout config -- a `kind: Canary`
(Flagger) or `kind: Rollout` (Argo Rollouts) CRD anywhere in the tree."""
from __future__ import annotations

from .models import CANARY_ROLLOUT_CRD_KINDS


def _has_canary_rollout_config(k8s_docs: list[dict]) -> bool:
    return any(doc.get("kind") in CANARY_ROLLOUT_CRD_KINDS for doc in k8s_docs)
