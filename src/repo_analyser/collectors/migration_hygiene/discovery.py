"""Finds migration files for the two conventions this collector supports
-- Django (`*/migrations/NNNN_*.py`) and Alembic (`*/alembic/versions/
*.py` with `upgrade()`/`downgrade()`) -- plus paired plain-SQL migrations
(`*.up.sql`/`*.down.sql`, the Flyway/golang-migrate/dbmate shape).

Walks the filesystem (like api_contract/discovery.py, depgraph.py,
duplication.py), not `git ls-files` -- same rationale: a gitignored-but-
present migration file is still a real file a developer or CI could run,
so this follows the rest of the codebase's convention rather than
inventing a second exclusion policy.

A single bounded walk finds all three shapes at once so a large repo (the
"50k files" edge case) is walked once, not three times.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from .patterns import DJANGO_MIGRATION_RE, SQL_DOWN_RE, SQL_UP_RE


@dataclass
class DiscoveredMigrations:
    django_files: list[Path] = field(default_factory=list)
    alembic_files: list[Path] = field(default_factory=list)
    sql_up_files: list[Path] = field(default_factory=list)
    sql_down_files: list[Path] = field(default_factory=list)
    # True the moment a directory literally named "migrations" (or an
    # alembic "versions" dir) exists, even with zero recognized files in
    # it -- distinguishes "no migrations dir at all" from "a migrations
    # dir that exists but is empty/unrecognized" (AGENTS.md §3 rung 1 vs 2).
    saw_migrations_dir: bool = False


def _is_alembic_versions_dir(p: Path) -> bool:
    return p.name == "versions" and "alembic" in {part.lower() for part in p.parts}


def discover_migrations(repo: Path) -> DiscoveredMigrations:
    result = DiscoveredMigrations()
    for p in repo.rglob("*"):
        if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue

        if p.is_dir():
            # Registers a *directory* the moment it exists, even with zero
            # files in it -- rglob("*") never yields anything "inside" an
            # empty directory, so an empty-dir check has to happen here,
            # not in the is_file() branch below (AGENTS.md §3 rung 1 vs 2:
            # "no migrations dir at all" vs "one that exists but is empty").
            if p.name == "migrations" or _is_alembic_versions_dir(p):
                result.saw_migrations_dir = True
            continue

        if not p.is_file():
            continue  # symlink to a missing target, socket, etc. -- never a migration

        # SQL up/down pairs are a filename convention, not a directory
        # convention (unlike Django/Alembic) -- checked independently of
        # parent-dir name so a "*.up.sql" living inside a "migrations/"
        # dir (a very common real layout) is still recognized as the SQL
        # pair it is, not swallowed by the Django branch below.
        if p.suffix.lower() == ".sql" and (SQL_UP_RE.match(p.name) or SQL_DOWN_RE.match(p.name)):
            if SQL_UP_RE.match(p.name):
                result.sql_up_files.append(p)
            else:
                result.sql_down_files.append(p)
            continue

        if p.parent.name == "migrations":
            if p.suffix == ".py" and p.name != "__init__.py" and DJANGO_MIGRATION_RE.match(p.name):
                result.django_files.append(p)
            continue

        if _is_alembic_versions_dir(p.parent):
            if p.suffix == ".py" and p.name != "__init__.py":
                result.alembic_files.append(p)
            continue

    return result
