"""Data & Persistence Layer static-signal detection: migration
reversibility, orphaned/duplicate migration files, committed database
file/dump hygiene, and a PII-column-name inventory -- the four criteria
in docs/checklist-by-repo-type/single-repo.md's "Data & Persistence
Layer" section answerable from static repo/git inspection alone. See
docs/METHODOLOGY.md for the exact detection method per signal and the
full, honest list of what this does NOT cover (everything else in that
checklist section needs a live DB connection or executing the target
repo's own toolchain -- out of scope for this collector by design, see
docs/ARCHITECTURE.md's security model / AGENTS.md §2.2).

Four signals, checked and reported independently -- never averaged into
one score (docs/ARCHITECTURE.md's "two tools measuring the same thing
stay two separate outputs" rule):

  1. migration_convention/migration_file_count/reversible_count/
     irreversible_count/reversibility_unknown_count -- which migration
     convention(s) this repo uses (Django `*/migrations/NNNN_*.py`,
     Alembic `*/alembic/versions/*.py`, or paired plain-SQL `*.up.sql`/
     `*.down.sql`), and, per file, whether a reverse path exists. Only
     these two conventions plus paired SQL are supported; anything else
     reports migration_convention="none" rather than guessing.
  2. orphaned_migration_count/orphaned_migrations,
     duplicate_migration_count/duplicate_migrations -- a Django
     migration's `dependencies` naming a same-app sibling this collector
     never found (orphan), and byte-identical files or two files sharing
     the same leading migration number (duplicate).
  3. committed_db_file_count/committed_db_files,
     committed_sql_dump_count/committed_sql_dumps -- a SQLite file
     (confirmed by its 16-byte magic header) or a real pg_dump/mysqldump
     output (confirmed by its own signature, not merely "contains
     INSERT") committed anywhere in git history, current tree or not.
  4. pii_column_match_count/pii_columns_sample -- column/field names
     matching a PII-name heuristic (email, ssn, phone, dob, password,
     credit_card, ...), found in the migration files this collector
     already discovered. A "here's where to look" inventory, not a
     judgment on whether the data is properly protected.

skip_reason is populated only when migration_convention is "none" (mirrors
api_contract.py's own skip_reason exactly) -- the committed-db-file and
PII signals are still real, independent findings even for a repo with no
recognized migration convention (e.g. a repo with a bare committed
`prod.sqlite` and nothing else).

Deliberate v1 scope, stated honestly: this is static file/git-history
inspection -- it does not connect to a live database, execute a
migration, or diff a real schema. Reversibility signals report whether a
reverse *path* exists (structurally), never whether it is *correct*.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import MigrationHygieneResult
from .runner import run_migration_hygiene

__all__ = ["MigrationHygieneResult", "analyze_repo", "run_migration_hygiene"]
