"""Portfolio-wide entrypoint: write one CSV row per repo plus a summary
JSON of aggregate counts -- mirrors performance.py's own run_performance
shape."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import ObservabilityResult


def run_observability(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "observability.csv"
    write_csv(out_path, rows, fieldnames=ObservabilityResult)
    write_json(out_dir / "observability_summary.json", {
        "repos_total": len(rows),
        "repos_with_structured_logging": sum(1 for r in rows if r["has_structured_logging"]),
        "repos_with_metrics_lib": sum(1 for r in rows if r["has_metrics_lib"]),
        "repos_with_tracing": sum(1 for r in rows if r["has_tracing"]),
        "repos_with_k8s_health_probes": sum(1 for r in rows if r["has_k8s_health_probes"]),
    })
    return out_path
