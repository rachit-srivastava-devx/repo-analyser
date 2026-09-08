"""Per-repo orchestration: combines discovery, per-convention scanning
(conventions.py), committed-db-file, and PII-inventory detection into one
MigrationHygieneResult. See package docstring for the full contract."""
from __future__ import annotations

from pathlib import Path

from .conventions import scan_conventions
from .db_files import find_committed_db_files
from .discovery import discover_migrations
from .models import MigrationHygieneResult
from .patterns import SAMPLE_CAP
from .pii import find_pii_columns
from .text_io import join_sample


def analyze_repo(repo: Path) -> MigrationHygieneResult:
    disc = discover_migrations(repo)
    scan = scan_conventions(disc)

    db_files = find_committed_db_files(repo)
    sqlite_hits = [f"{f.path}(tracked={f.still_in_working_tree})" for f in db_files if f.kind == "sqlite"]
    dump_hits = [f"{f.path}(tracked={f.still_in_working_tree})" for f in db_files if f.kind == "sql_dump"]

    pii_matches: list[str] = []
    for f in scan.all_files:
        pii_matches += find_pii_columns(f)

    if scan.conventions:
        skip_reason = ""
    elif disc.saw_migrations_dir:
        skip_reason = "migrations directory found but empty, or convention not recognized"
    else:
        skip_reason = "no migration directory or file convention detected"

    return MigrationHygieneResult(
        repo=repo.name,
        migration_convention=";".join(scan.conventions) if scan.conventions else "none",
        migration_file_count=len(scan.all_files),
        reversible_count=scan.reversible,
        irreversible_count=scan.irreversible,
        reversibility_unknown_count=scan.unknown,
        orphaned_migration_count=len(scan.orphans),
        orphaned_migrations=join_sample(sorted(scan.orphans), SAMPLE_CAP),
        duplicate_migration_count=len(scan.duplicates),
        duplicate_migrations=join_sample(sorted(scan.duplicates), SAMPLE_CAP),
        committed_db_file_count=len(sqlite_hits),
        committed_db_files=join_sample(sorted(sqlite_hits), SAMPLE_CAP),
        committed_sql_dump_count=len(dump_hits),
        committed_sql_dumps=join_sample(sorted(dump_hits), SAMPLE_CAP),
        pii_column_match_count=len(pii_matches),
        pii_columns_sample=join_sample(sorted(pii_matches), SAMPLE_CAP),
        skip_reason=skip_reason,
    )
