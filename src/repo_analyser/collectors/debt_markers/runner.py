"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary -- same shape as flag_debt/runner.py and codebase_modularity/
runner.py (write_csv/write_json from core.util, dataclass type passed
directly as fieldnames)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import DebtMarkersResult


def run_debt_markers(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "debt_markers.csv"
    write_csv(out_path, rows, fieldnames=DebtMarkersResult)
    write_json(out_dir / "debt_markers_summary.json", {
        "repos_total": len(rows),
        "repos_skipped": sum(1 for r in rows if r["skip_reason"]),
        "total_markers": sum(r["total_marker_count"] for r in rows),
        "total_stale_markers": sum(r["stale_marker_count"] for r in rows),
        "repos_with_markers": sum(1 for r in rows if r["total_marker_count"] > 0),
    })
    return out_path
