"""Per-convention migration scan: for each supported convention (Django,
Alembic, paired SQL) found by discovery.py, combines that convention's own
reversibility tally (reversibility_tally.py), duplicate detection
(orphans.py), and -- Django only -- orphan detection (django_orphans.py)
into one accumulated `ConventionScan`. Split out of analyze.py's per-repo
orchestration to keep both under the ~80-line convention (AGENTS.md §4):
analyze_repo stays a pure composition of discover_migrations + this scan +
the two convention-independent signals (committed DB files, PII).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .alembic_reversibility import classify_alembic
from .discovery import DiscoveredMigrations
from .django_orphans import find_django_orphans
from .orphans import find_duplicate_files, find_duplicate_numbers, find_duplicate_numbers_by_group
from .patterns import SQL_DOWN_RE, SQL_UP_RE
from .reversibility import classify_django, classify_sql_pair
from .reversibility_tally import tally_reversibility


@dataclass
class ConventionScan:
    conventions: list[str] = field(default_factory=list)
    all_files: list[Path] = field(default_factory=list)
    reversible: int = 0
    irreversible: int = 0
    unknown: int = 0
    orphans: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)

    def _add_tally(self, counts: tuple[int, int, int]) -> None:
        r, i, u = counts
        self.reversible += r
        self.irreversible += i
        self.unknown += u


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


def scan_conventions(disc: DiscoveredMigrations) -> ConventionScan:
    scan = ConventionScan()

    if disc.django_files:
        scan.conventions.append("django")
        scan.all_files += disc.django_files
        scan._add_tally(tally_reversibility(disc.django_files, classify_django))
        scan.orphans += find_django_orphans(disc.django_files)
        scan.duplicates += find_duplicate_files(disc.django_files)
        # Scoped per app (p.parent.parent.name, same key find_django_orphans
        # groups by) -- unlike SQL/Alembic, every Django app conventionally
        # restarts its own numbering at 0001, so two unrelated apps each
        # having their own legitimate 0001_initial.py must not be flagged.
        scan.duplicates += find_duplicate_numbers_by_group(disc.django_files, key=lambda p: p.parent.parent.name)

    if disc.alembic_files:
        scan.conventions.append("alembic")
        scan.all_files += disc.alembic_files
        scan._add_tally(tally_reversibility(disc.alembic_files, classify_alembic))
        scan.duplicates += find_duplicate_files(disc.alembic_files)

    if disc.sql_up_files:
        scan.conventions.append("sql_pairs")
        scan.all_files += disc.sql_up_files + disc.sql_down_files
        scan._add_tally(tally_reversibility(
            disc.sql_up_files, lambda up: classify_sql_pair(_sql_down_for(up, disc.sql_down_files))
        ))
        scan.duplicates += find_duplicate_files(disc.sql_up_files)
        scan.duplicates += find_duplicate_numbers(disc.sql_up_files)

    return scan
