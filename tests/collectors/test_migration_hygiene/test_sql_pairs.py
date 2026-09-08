from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.discovery import discover_migrations
from repo_analyser.collectors.migration_hygiene.reversibility import classify_sql_pair

from ._migration_hygiene_helpers import write


def test_missing_down_file_is_irreversible() -> None:
    assert classify_sql_pair(None) == "irreversible"


def test_present_down_file_is_reversible(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/001_x.down.sql", "DROP TABLE users;")
    assert classify_sql_pair(p) == "reversible"


def test_empty_down_file_is_irreversible(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/001_x.down.sql", "   \n  ")
    assert classify_sql_pair(p) == "irreversible"


def test_unreadable_down_file_is_unknown(tmp_path: Path) -> None:
    p = tmp_path / "migrations" / "001_x.down.sql"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe\x00not-utf8")
    assert classify_sql_pair(p) == "unknown"


def test_discovery_finds_up_and_down_pairs_case_insensitively(tmp_path: Path) -> None:
    write(tmp_path, "migrations/001_create_users.up.sql", "CREATE TABLE users (id INT);")
    write(tmp_path, "migrations/001_create_users.DOWN.SQL", "DROP TABLE users;")
    write(tmp_path, "migrations/002_add_col.up.sql", "ALTER TABLE users ADD COLUMN x INT;")
    result = discover_migrations(tmp_path)
    assert len(result.sql_up_files) == 2
    assert len(result.sql_down_files) == 1
    assert result.saw_migrations_dir is True


def test_sql_pair_lives_outside_a_dir_named_migrations(tmp_path: Path) -> None:
    """SQL up/down pairing is a filename convention, not a directory-name
    convention -- must still be found under e.g. "db/sql/"."""
    write(tmp_path, "db/sql/001_create.up.sql", "CREATE TABLE t (id INT);")
    write(tmp_path, "db/sql/001_create.down.sql", "DROP TABLE t;")
    result = discover_migrations(tmp_path)
    assert len(result.sql_up_files) == 1
    assert len(result.sql_down_files) == 1
