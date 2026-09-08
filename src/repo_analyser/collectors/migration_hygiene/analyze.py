"""Per-repo orchestration: combines discovery, reversibility, orphan/
duplicate, committed-db-file, and PII-inventory detection into one
MigrationHygieneResult. See package docstring for the full contract."""
from __future__ import annotations

from pathlib import Path

from .alembic_reversibility import classify_alembic
from .db_files import find_committed_db_files
from .discovery import discover_migrations
from .django_orphans import find_django_orphans
from .models import MigrationHygieneResult
from .orphans import find_duplicate_files, find_duplicate_numbers
from .patterns import SAMPLE_CAP, SQL_DOWN_RE, SQL_UP_RE
from .pii import find_pii_columns
from .reversibility import classify_django, classify_sql_pair
from .text_io import join_sample


def _sql_down_for(up: Path, sql_down_files: list[Path]) -> Path | None:
    """Matches "NNN_desc.up.sql" to its "NNN_desc.down.sql" pair by the
    shared prefix both regexes capture -- not string-slicing on a literal
    ".up.sql" suffix, which would break case-insensitively (SQL_UP_RE/
    SQL_DOWN_RE both match ".UP.SQL"/".DOWN.SQL" too)."""
    up_match = SQL_UP_RE.match(up.name)
    if not up_match:
        return None
    prefix = up_match.group("num")
    for down in sql_down_files:
        down_match = SQL_DOWN_RE.match(down.name)
        if down_match and down_match.group("num") == prefix:
            return down
    return None


def analyze_repo(repo: Path) -> MigrationHygieneResult:
    disc = discover_migrations(repo)
    conventions = []
    reversible = irreversible = unknown = 0
    all_files: list[Path] = []
    orphans: list[str] = []
    duplicates: list[str] = []

    if disc.django_files:
        conventions.append("django")
        all_files += disc.django_files
        for f in disc.django_files:
            state = classify_django(f)
            reversible += state == "reversible"
            irreversible += state == "irreversible"
            unknown += state == "unknown"
        orphans += find_django_orphans(disc.django_files)
        duplicates += find_duplicate_files(disc.django_files)
        duplicates += find_duplicate_numbers(disc.django_files)

    if disc.alembic_files:
        conventions.append("alembic")
        all_files += disc.alembic_files
        for f in disc.alembic_files:
            state = classify_alembic(f)
            reversible += state == "reversible"
            irreversible += state == "irreversible"
            unknown += state == "unknown"
        duplicates += find_duplicate_files(disc.alembic_files)

    if disc.sql_up_files:
        conventions.append("sql_pairs")
        all_files += disc.sql_up_files + disc.sql_down_files
        for up in disc.sql_up_files:
            state = classify_sql_pair(_sql_down_for(up, disc.sql_down_files))
            reversible += state == "reversible"
            irreversible += state == "irreversible"
            unknown += state == "unknown"
        duplicates += find_duplicate_files(disc.sql_up_files)
        duplicates += find_duplicate_numbers(disc.sql_up_files)

    db_files = find_committed_db_files(repo)
    sqlite_hits = [f"{f.path}(tracked={f.still_in_working_tree})" for f in db_files if f.kind == "sqlite"]
    dump_hits = [f"{f.path}(tracked={f.still_in_working_tree})" for f in db_files if f.kind == "sql_dump"]

    pii_matches: list[str] = []
    for f in all_files:
        pii_matches += find_pii_columns(f)

    if conventions:
        skip_reason = ""
    elif disc.saw_migrations_dir:
        skip_reason = "migrations directory found but empty, or convention not recognized"
    else:
        skip_reason = "no migration directory or file convention detected"

    return MigrationHygieneResult(
        repo=repo.name,
        migration_convention=";".join(conventions) if conventions else "none",
        migration_file_count=len(all_files),
        reversible_count=reversible,
        irreversible_count=irreversible,
        reversibility_unknown_count=unknown,
        orphaned_migration_count=len(orphans),
        orphaned_migrations=join_sample(sorted(orphans), SAMPLE_CAP),
        duplicate_migration_count=len(duplicates),
        duplicate_migrations=join_sample(sorted(duplicates), SAMPLE_CAP),
        committed_db_file_count=len(sqlite_hits),
        committed_db_files=join_sample(sorted(sqlite_hits), SAMPLE_CAP),
        committed_sql_dump_count=len(dump_hits),
        committed_sql_dumps=join_sample(sorted(dump_hits), SAMPLE_CAP),
        pii_column_match_count=len(pii_matches),
        pii_columns_sample=join_sample(sorted(pii_matches), SAMPLE_CAP),
        skip_reason=skip_reason,
    )
