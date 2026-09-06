"""Portfolio-level entrypoint: writes one CSV row per repo, plus a
summary JSON of repo-level counts."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo


def run_microservices_topology(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "microservices_topology.csv"
    write_csv(out_path, rows)
    analyzed = [r for r in rows if not r["skip_reason"]]
    write_json(out_dir / "microservices_topology_summary.json", {
        "repos_total": len(rows),
        "repos_analyzed": len(analyzed),
        "repos_with_dependency_cycle": sum(1 for r in analyzed if r["has_dependency_cycle"]),
        "repos_with_service_mesh": sum(1 for r in analyzed if r["has_service_mesh"]),
        "repos_with_network_policy_default_deny":
            sum(1 for r in analyzed if r["has_network_policy_default_deny"]),
        "repos_with_canary_rollout_config": sum(1 for r in analyzed if r["has_canary_rollout_config"]),
    })
    return out_path
