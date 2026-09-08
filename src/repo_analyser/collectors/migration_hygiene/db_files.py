"""Committed database file / SQL dump hygiene -- full git history, not
just the working tree (a file removed in a later commit still bloats
every clone forever, and is still a real leak). Pure git, no external
tool, same "full history" mindset as security.py's gitleaks scan. See
git_blobs.py for the shared history-walking primitives.

Content-based, not extension-based (patterns.py's DUMP_SIGNATURES/
SQLITE_MAGIC): a SQLite file needs its 16-byte magic header, not just the
extension (the ".sqlite that's actually plain text" edge case); a `.sql`
file is a dump only with a pg_dump/mysqldump signature, never merely
"contains INSERT" (a migration inserting seed data is not a dump).

Deliberately NOT attempted: the checklist's "seed-data fixture holding
real (not synthetic) data" sub-case -- telling synthetic from real
personal data from static text alone isn't a heuristic this collector can
make honestly (docs/METHODOLOGY.md has the full limitations note).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .git_blobs import blob_content, blobs_by_path, still_tracked
from .patterns import DB_FILE_EXTENSIONS, DUMP_SIGNATURES, SQL_EXTENSION, SQLITE_MAGIC


@dataclass
class CommittedDbFile:
    path: str
    kind: str  # "sqlite" | "sql_dump"
    still_in_working_tree: bool


def _matches_candidate_extension(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(DB_FILE_EXTENSIONS) or lower.endswith(SQL_EXTENSION)


def find_committed_db_files(repo: Path) -> list[CommittedDbFile]:
    by_path = blobs_by_path(repo, _matches_candidate_extension)
    findings: list[CommittedDbFile] = []
    for path in sorted(by_path):
        contents = [blob_content(repo, sha) for sha in by_path[path]]
        if path.lower().endswith(DB_FILE_EXTENSIONS):
            if any(c.startswith(SQLITE_MAGIC) for c in contents):
                findings.append(CommittedDbFile(path, "sqlite", still_tracked(repo, path)))
        elif path.lower().endswith(SQL_EXTENSION):
            lowered_texts = [c.decode("utf-8", errors="ignore").lower() for c in contents]
            if any(sig in text for text in lowered_texts for sig in DUMP_SIGNATURES):
                findings.append(CommittedDbFile(path, "sql_dump", still_tracked(repo, path)))
    return findings
