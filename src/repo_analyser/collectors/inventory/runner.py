from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv
from .analyze import analyze_repo


def run_inventory(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    rows.sort(key=lambda r: -r["total_commits"])
    out_path = out_dir / "inventory.csv"
    write_csv(out_path, rows)
    return out_path
