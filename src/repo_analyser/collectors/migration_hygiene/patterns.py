"""Detection constants shared across this package's modules. Kept in one
place so a future convention/keyword addition is a one-file change, same
convention as api_contract/patterns.py."""
from __future__ import annotations

import re

# Bounded sample size for every ";"-joined list field in the result --
# an unbounded join is how a monorepo with 50k migration files (AGENTS.md
# §3's "huge" rung) turns one CSV cell into a multi-megabyte string. Every
# joiner in this package appends "+N more" when it truncates, and the
# corresponding *_count field always reports the true total, never the
# truncated sample's length.
SAMPLE_CAP = 25

# -- Migration-convention filename shapes -----------------------------------
DJANGO_MIGRATION_RE = re.compile(r"^\d{4}_.*\.py$")
ALEMBIC_VERSIONS_DIR = "versions"
SQL_UP_RE = re.compile(r"^(?P<num>[^/\\]*?)\.up\.sql$", re.IGNORECASE)
SQL_DOWN_RE = re.compile(r"^(?P<num>[^/\\]*?)\.down\.sql$", re.IGNORECASE)

# -- Committed database file / dump detection -------------------------------
SQLITE_MAGIC = b"SQLite format 3\x00"
DB_FILE_EXTENSIONS = (".sqlite", ".sqlite3", ".db")
SQL_EXTENSION = ".sql"

# A real pg_dump/mysqldump output carries one of these header/body
# signatures; a hand-written migration that happens to INSERT seed data
# does not -- this is the precise, content-based distinction the package
# docstring commits to (as opposed to db_hygiene.py's coarser
# extension+size heuristic for a different, adjacent measured dimension).
DUMP_SIGNATURES = (
    "-- postgresql database dump",
    "-- mysql dump",
    "-- dumping data for table",
    "pg_dump",
    "mysqldump",
    "copy public.",  # `COPY public.<table> (...) FROM stdin;` -- pg_dump's data section
    "from stdin;",
)

# -- PII/sensitive column-name heuristic -------------------------------------
# Substring match against the lowercased column/field name -- deliberately
# broad (a "here's where to look" inventory, not a judgment call, see
# package docstring) but each entry is specific enough that a false
# positive is at least explicable (e.g. "dob" also matches "adobe_id",
# a known, accepted limitation of a substring heuristic -- documented in
# docs/METHODOLOGY.md rather than silently accepted).
PII_NAME_KEYWORDS = (
    "email", "ssn", "social_security", "phone", "address", "dob",
    "date_of_birth", "password", "passwd", "credit_card", "card_number",
    "ip_address", "national_id", "passport", "tax_id", "bank_account",
    "routing_number", "drivers_license", "medical", "health_record",
)
