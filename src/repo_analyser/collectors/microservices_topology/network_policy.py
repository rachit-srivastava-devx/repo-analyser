"""Signal (c): default-deny NetworkPolicy presence -- verified against
real Kubernetes docs (kubernetes.io/docs/concepts/services-networking/
network-policies, "Default deny all ingress traffic" / "Default deny all
egress traffic" / "Default deny all ingress and all egress traffic"): a
NetworkPolicy's `podSelector: {}` selects every pod in the namespace (a
non-empty selector is a scoped, per-workload policy, not the
namespace-wide "default deny" posture this checklist item means); for
each direction named in `policyTypes` (inferred per the k8s doc's own
rule when omitted -- see `_is_default_deny_network_policy`), an absent or
empty `ingress`/`egress` rule list means zero rules ever allow anything
through, i.e. deny-all for that direction. A non-empty rule list -- even
the documented `- {}` "match everything" allow-all shorthand -- is at
least one explicit ALLOW, so that policy is correctly NOT default-deny."""
from __future__ import annotations


def _is_default_deny_network_policy(doc: dict) -> bool:
    if doc.get("kind") != "NetworkPolicy":
        return False
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return False
    if spec.get("podSelector") != {}:
        # A scoped selector (or a missing, schema-invalid podSelector) is a
        # per-workload policy, not the namespace-wide "default deny"
        # posture this checklist item means -- only an empty podSelector
        # selects every pod in the namespace.
        return False
    policy_types = spec.get("policyTypes") or None
    if not policy_types:
        # k8s's own inference rule when policyTypes is omitted: Ingress is
        # always assumed; Egress only if an `egress` key is present at all.
        policy_types = ["Ingress"] + (["Egress"] if "egress" in spec else [])
    for direction, key in (("Ingress", "ingress"), ("Egress", "egress")):
        if direction in policy_types and spec.get(key):
            # A non-empty rule list -- even the documented `- {}` "match
            # everything" allow-all shorthand -- is at least one explicit
            # ALLOW, so this direction is not default-deny.
            return False
    return True


def _has_network_policy_default_deny(k8s_docs: list[dict]) -> bool:
    return any(_is_default_deny_network_policy(doc) for doc in k8s_docs)
