from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo


def run_license_compliance(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "license_compliance.csv"
    write_csv(out_path, rows)
    write_json(out_dir / "license_compliance_summary.json", {
        "repos_total": len(rows),
        "license_id_counts": dict(Counter(r["license_id"] for r in rows)),
        "repos_with_mismatch": sum(1 for r in rows if r["license_mismatch"]),
        "repos_with_dependencies_no_license": sum(1 for r in rows if r["has_dependencies_no_license"]),
    })
    return out_path
