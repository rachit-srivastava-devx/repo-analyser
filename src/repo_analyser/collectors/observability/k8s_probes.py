"""Kubernetes liveness/readinessProbe detection: either an actual probe key
found in any YAML under a deployment-shaped directory (k8s/, deploy/,
charts/, manifests/), or a bare Chart.yaml anywhere (Helm chart) as an
alternate, coarser signal for the same underlying "this is a k8s-deployed
service" question -- Chart.yaml itself never contains a probe key (it's
chart metadata: name/version/description), it's accepted deliberately as
its own, looser proxy, the same way performance.py's own
PERF_PACKAGE_JSON_KEYS accepts a bare config key as evidence without
inspecting its contents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ...core.lang import EXCLUDE_DIR_PARTS
from .models import K8S_DIR_NAMES, K8S_HEALTH_PROBE_KEYS


def k8s_shaped_dirs(repo: Path) -> list[Path]:
    """Every directory anywhere under repo whose name suggests deployment
    config, excluding the same vendored/build directories
    core.lang.EXCLUDE_DIR_PARTS already knows to skip -- so a coincidental
    "deploy" directory inside a vendored dependency tree doesn't count as
    this repo's own deployment config."""
    return [
        p for p in repo.rglob("*")
        if p.is_dir() and p.name in K8S_DIR_NAMES
        and not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)
    ]


def yaml_docs(text: str) -> list[Any]:
    """Every parsed document in a (possibly multi-document, "---"-
    separated) YAML file. Returns [] for anything that fails to parse --
    same "skip what can't be read, don't crash the whole collector"
    contract as performance.py's own _load_workflow_docs."""
    try:
        return [doc for doc in yaml.safe_load_all(text) if doc is not None]
    except yaml.YAMLError:
        return []


def contains_health_probe_key(node: Any) -> bool:
    if isinstance(node, dict):
        if K8S_HEALTH_PROBE_KEYS & node.keys():
            return True
        return any(contains_health_probe_key(v) for v in node.values())
    if isinstance(node, list):
        return any(contains_health_probe_key(item) for item in node)
    return False


def has_health_probes_in_k8s_dirs(repo: Path) -> bool:
    for d in k8s_shaped_dirs(repo):
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in (".yaml", ".yml"):
                if any(contains_health_probe_key(doc) for doc in yaml_docs(f.read_text(errors="replace"))):
                    return True
    return False


def has_chart_yaml(repo: Path) -> bool:
    return any(
        not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)
        for p in repo.rglob("Chart.yaml")
    )


def detect_k8s_health_probes(repo: Path) -> bool:
    return has_health_probes_in_k8s_dirs(repo) or has_chart_yaml(repo)


def has_any_k8s_signal_source(repo: Path) -> bool:
    return bool(k8s_shaped_dirs(repo)) or has_chart_yaml(repo)
