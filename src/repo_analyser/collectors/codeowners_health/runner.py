from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo


def run_codeowners_health(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "codeowners_health.csv"
    write_csv(out_path, rows)
    with_codeowners = sum(1 for r in rows if r["has_codeowners"])
    coverages = [r["coverage_pct"] for r in rows]
    average_coverage = round(sum(coverages) / len(coverages), 2) if coverages else 0.0
    write_json(out_dir / "codeowners_health_summary.json", {
        "repos_total": len(rows),
        "repos_with_codeowners": with_codeowners,
        "repos_without_codeowners": len(rows) - with_codeowners,
        "average_coverage_pct": average_coverage,
    })
    return out_path
