"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary. write_csv() takes the dataclass type directly (post-hardening
call-site convention, matches migration_hygiene/api_contract/flag_debt)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import CodebaseModularityResult


def run_codebase_modularity(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "codebase_modularity.csv"
    write_csv(out_path, rows, CodebaseModularityResult)
    write_json(out_dir / "codebase_modularity_summary.json", {
        "repos_total": len(rows),
        "repos_with_oversized_files": sum(1 for r in rows if r["oversized_file_count"] > 0),
        "oversized_files_total": sum(r["oversized_file_count"] for r in rows),
        "oversized_packages_total": sum(r["oversized_package_count"] for r in rows),
        "god_classes_total": sum(r["god_class_count"] for r in rows),
        "repos_with_layering_enforcement": sum(1 for r in rows if r["layering_tool_detected"]),
    })
    return out_path
