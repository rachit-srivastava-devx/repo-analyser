"""Per-repo orchestration: combine the three manifest-based library signals
with the k8s health-probe signal, and decide whether this repo has nothing
at all to report (skip_reason) versus a real "checked, found none" result.
"""
from __future__ import annotations

from pathlib import Path

from .dependencies import all_declared_dependencies, detect_logging_libs, detect_metrics_libs, detect_tracing_libs
from .k8s_probes import detect_k8s_health_probes, has_any_k8s_signal_source
from .models import RECOGNIZED_MANIFEST_FILENAMES, ObservabilityResult


def has_any_recognized_manifest(repo: Path) -> bool:
    return any((repo / name).exists() for name in RECOGNIZED_MANIFEST_FILENAMES)


def analyze_repo(repo: Path) -> ObservabilityResult:
    all_deps = all_declared_dependencies(repo)
    logging_libs = detect_logging_libs(all_deps)
    tracing_libs = detect_tracing_libs(all_deps)
    metrics_libs = detect_metrics_libs(all_deps)
    has_k8s = detect_k8s_health_probes(repo)

    if not has_any_recognized_manifest(repo) and not has_any_k8s_signal_source(repo):
        return ObservabilityResult(
            repo=repo.name,
            has_structured_logging=False, logging_lib="",
            has_metrics_lib=False, metrics_lib="",
            has_tracing=False, tracing_lib="",
            has_k8s_health_probes=False,
            skip_reason=(
                "no observability signal found: no recognized dependency manifest "
                "(package.json, requirements.txt, pyproject.toml, go.mod) and no "
                "k8s-shaped directory (k8s/, deploy/, charts/, manifests/) or Chart.yaml"
            ),
        )

    return ObservabilityResult(
        repo=repo.name,
        has_structured_logging=bool(logging_libs), logging_lib=";".join(sorted(logging_libs)),
        has_metrics_lib=bool(metrics_libs), metrics_lib=";".join(sorted(metrics_libs)),
        has_tracing=bool(tracing_libs), tracing_lib=";".join(sorted(tracing_libs)),
        has_k8s_health_probes=has_k8s,
        skip_reason="",
    )
