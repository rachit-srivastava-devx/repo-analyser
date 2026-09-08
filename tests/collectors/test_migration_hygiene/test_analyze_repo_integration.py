"""End-to-end analyze_repo() coverage across all three supported
conventions -- the unit tests elsewhere in this package cover each
detection function in isolation; these confirm analyze_repo's own
orchestration (which convention branch runs, how per-convention
reversibility counts combine, and skip_reason) end to end."""
from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.analyze import analyze_repo

from ._migration_hygiene_helpers import (
    ALEMBIC_EMPTY_DOWNGRADE,
    ALEMBIC_REAL_DOWNGRADE,
    commit_all,
    init_repo,
    write,
)


def test_alembic_convention_end_to_end(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "alembic/versions/abc123_add_users.py", ALEMBIC_REAL_DOWNGRADE)
    write(repo, "alembic/versions/def456_fake_empty.py", ALEMBIC_EMPTY_DOWNGRADE)
    commit_all(repo, "alembic migrations")

    result = analyze_repo(repo)
    assert result.migration_convention == "alembic"
    assert result.migration_file_count == 2
    assert result.reversible_count == 1
    assert result.irreversible_count == 1
    assert result.skip_reason == ""


def test_sql_pairs_convention_end_to_end(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "migrations/001_create_users.up.sql",
          "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));")
    write(repo, "migrations/001_create_users.down.sql", "DROP TABLE users;")
    write(repo, "migrations/002_add_phone.up.sql", "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);")
    # 002 deliberately has no down file -- irreversible
    commit_all(repo, "sql migrations")

    result = analyze_repo(repo)
    assert result.migration_convention == "sql_pairs"
    assert result.migration_file_count == 3  # 2 .up.sql + 1 .down.sql
    assert result.reversible_count == 1
    assert result.irreversible_count == 1
    assert result.pii_column_match_count == 2  # email + phone_number


def test_duplicate_and_orphan_reported_through_analyze_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "app/migrations/0001_initial.py", "dependencies = []\n")
    # same leading number as 0001_initial.py above, different content
    write(repo, "app/migrations/0001_dup.py", "dependencies = ['different']\n")
    write(repo, "app/migrations/0002_orphan.py", 'dependencies = [("app", "9999_missing")]\n')
    commit_all(repo, "django migrations with issues")

    result = analyze_repo(repo)
    assert result.migration_convention == "django"
    assert result.duplicate_migration_count == 1  # same-number signal only; content differs
    assert result.orphaned_migration_count == 1
    assert "0002_orphan.py->9999_missing" in result.orphaned_migrations
