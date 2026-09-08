"""Dependency-token -> library-label lookup tables, one per signal category,
spanning all three languages this tool understands (JS/TS, Python, Go) --
unlike performance.py (JS-only), an observability posture question applies
just as much to a Python or Go service.

Tracing is reported as its own has_tracing/tracing_lib pair, separate from
logging, even though OpenTelemetry's own docs describe one SDK as covering
logs, metrics, and traces alike: the CSV contract for this module keeps
tracing and structured-logging as two separate labeled columns (AGENTS.md
#4 -- two questions that are actually different stay two separate, labeled
outputs, never averaged into one), so each library maps to exactly one of
"logging" or "tracing," never both.

JS package names, normalized PyPI names, and Go module paths never collide
with each other in practice (disjoint character sets/naming conventions),
so one merged dict per category + one membership check is enough --
mirrors performance.py's own PERF_PACKAGE_SIGNALS shape, just widened
from one ecosystem to three.
"""
from __future__ import annotations

JS_LOGGING_PACKAGES = {"winston": "winston", "pino": "pino"}
PY_LOGGING_PACKAGES = {"structlog": "structlog"}  # normalized PyPI name
GO_LOGGING_MODULES = {"github.com/rs/zerolog": "zerolog"}

JS_TRACING_PACKAGES = {"@opentelemetry/api": "opentelemetry"}
PY_TRACING_PACKAGES = {"opentelemetry-api": "opentelemetry"}
GO_TRACING_MODULES = {"go.opentelemetry.io/otel": "opentelemetry"}

JS_METRICS_PACKAGES = {"prom-client": "prom-client"}
PY_METRICS_PACKAGES = {"prometheus-client": "prometheus_client"}  # PyPI dist name, normalized
GO_METRICS_MODULES = {"github.com/prometheus/client_golang": "prometheus_client"}

LOGGING_SIGNALS: dict[str, str] = {**JS_LOGGING_PACKAGES, **PY_LOGGING_PACKAGES, **GO_LOGGING_MODULES}
TRACING_SIGNALS: dict[str, str] = {**JS_TRACING_PACKAGES, **PY_TRACING_PACKAGES, **GO_TRACING_MODULES}
METRICS_SIGNALS: dict[str, str] = {**JS_METRICS_PACKAGES, **PY_METRICS_PACKAGES, **GO_METRICS_MODULES}
