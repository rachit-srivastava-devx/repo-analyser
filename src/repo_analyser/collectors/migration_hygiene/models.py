"""Result dataclass for the migration_hygiene collector. See package
docstring (__init__.py) for the full contract; see patterns.py for the
detection constants used by discovery.py/reversibility.py/orphans.py/
db_files.py/pii.py."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MigrationHygieneResult:
    repo: str
    migration_convention: str
    migration_file_count: int
    reversible_count: int
    irreversible_count: int
    reversibility_unknown_count: int
    orphaned_migration_count: int
    orphaned_migrations: str
    duplicate_migration_count: int
    duplicate_migrations: str
    committed_db_file_count: int
    committed_db_files: str
    committed_sql_dump_count: int
    committed_sql_dumps: str
    pii_column_match_count: int
    pii_columns_sample: str
    skip_reason: str
