from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo


def run_flag_debt(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "flag_debt.csv"
    write_csv(out_path, rows)
    repos_with_sdk = sum(1 for r in rows if r["sdk_detected"])
    write_json(out_dir / "flag_debt_summary.json", {
        "repos_total": len(rows),
        "repos_with_sdk_detected": repos_with_sdk,
        "total_flags_referenced": sum(r["flags_referenced_count"] for r in rows),
        "total_flags_defined": sum(r["flags_defined_count"] for r in rows),
        "total_orphaned_definitions": sum(
            1 for r in rows for f in r["orphaned_flag_definitions"].split(";") if f
        ),
        "total_undefined_references": sum(
            1 for r in rows for f in r["undefined_flag_references"].split(";") if f
        ),
    })
    return out_path
