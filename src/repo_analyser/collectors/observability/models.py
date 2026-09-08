"""Result shape + the small cross-cutting constants every signal module
needs (recognized manifest filenames, k8s-shaped directory names, and the
two health-probe keys) -- kept together because they're not any one
signal's own vocabulary, unlike the JS/Python/Go package-name tables which
live next to the manifest reader that consumes them.
"""
from __future__ import annotations

from dataclasses import dataclass

# Recognized dependency-manifest filenames across all three languages --
# used only to decide whether skip_reason applies (see analyze.py): a
# manifest existing but declaring none of our known library names is a
# real, legitimate "checked, found none" result, not a skip.
RECOGNIZED_MANIFEST_FILENAMES = ("package.json", "requirements.txt", "pyproject.toml", "go.mod")

# A directory name that suggests deployment/k8s manifest config, anywhere
# in the repo tree (not just at the root -- a service repo commonly nests
# this under e.g. deploy/k8s/ or infra/charts/).
K8S_DIR_NAMES = {"k8s", "deploy", "charts", "manifests"}

# The two k8s health-probe keys this module looks for, at any YAML nesting
# depth (real manifests nest these several levels deep, e.g.
# spec.template.spec.containers[].livenessProbe).
K8S_HEALTH_PROBE_KEYS = {"livenessProbe", "readinessProbe"}


@dataclass
class ObservabilityResult:
    repo: str
    has_structured_logging: bool
    logging_lib: str
    has_metrics_lib: bool
    metrics_lib: str
    has_tracing: bool
    tracing_lib: str
    has_k8s_health_probes: bool
    skip_reason: str
