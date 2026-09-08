"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary. write_csv() takes the dataclass type directly (post-hardening
call-site convention, matches api_contract/flag_debt)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import MigrationHygieneResult


def run_migration_hygiene(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "migration_hygiene.csv"
    write_csv(out_path, rows, MigrationHygieneResult)
    write_json(out_dir / "migration_hygiene_summary.json", {
        "repos_total": len(rows),
        "repos_with_recognized_convention": sum(1 for r in rows if r["migration_convention"] != "none"),
        "irreversible_migrations_total": sum(r["irreversible_count"] for r in rows),
        "reversibility_unknown_total": sum(r["reversibility_unknown_count"] for r in rows),
        "orphaned_migrations_total": sum(r["orphaned_migration_count"] for r in rows),
        "duplicate_migrations_total": sum(r["duplicate_migration_count"] for r in rows),
        "committed_db_files_total": sum(r["committed_db_file_count"] for r in rows),
        "committed_sql_dumps_total": sum(r["committed_sql_dump_count"] for r in rows),
        "pii_column_matches_total": sum(r["pii_column_match_count"] for r in rows),
    })
    return out_path
