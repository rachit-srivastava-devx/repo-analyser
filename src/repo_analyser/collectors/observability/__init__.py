"""Observability posture detection: does this repo declare structured
logging, a metrics-library dependency, distributed-tracing instrumentation,
or Kubernetes liveness/readiness health probes -- mirrors performance.py's
own "presence via manifest parsing, no subprocess, no external tool" shape
(see docs/ROADMAP.md's observability.py entry under "New collectors").

v1 scope, stated honestly: presence-only detection via dependency-manifest
and manifest-YAML parsing. It answers "is the library/config declared,"
not "is it actually wired up and emitting real telemetry at runtime" -- the
same scope line performance.py and e2e_quality.py already draw for their
own signals.

Four independent detection signals, spanning all three languages this tool
already understands (JS/TS, Python, Go): structured-logging library
presence (winston/pino, structlog, zerolog), metrics-library presence
(prom-client, prometheus_client, client_golang), distributed-tracing
library presence (@opentelemetry/api, opentelemetry-api,
go.opentelemetry.io/otel), and k8s liveness/readinessProbe keys (or a bare
Chart.yaml). See lib_tables.py and k8s_probes.py for the full writeup of
each signal's own reasoning.

Package layout (AGENTS.md #4 -- one file per concern, none over ~80
lines): models.py (result dataclass + shared constants), lib_tables.py
(per-signal dependency-token -> label lookups), manifest_js.py/
manifest_python.py/manifest_go.py (one manifest reader per language),
dependencies.py (merges the three + matches against lib_tables), k8s_probes.py
(the health-probe/Chart.yaml signal), analyze.py (per-repo orchestration,
including the skip_reason decision), runner.py (portfolio CSV-writing
entrypoint). Only this file's re-exports are the public API -- no other
module may import an observability submodule directly (this collector's
own tests are the one carve-out, per AGENTS.md #4).
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import ObservabilityResult
from .runner import run_observability

__all__ = [
    "ObservabilityResult",
    "analyze_repo",
    "run_observability",
]
