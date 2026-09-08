from __future__ import annotations

import sqlite3
from pathlib import Path

from repo_analyser.collectors.migration_hygiene.db_files import find_committed_db_files

from ._migration_hygiene_helpers import commit_all, init_repo, write, write_bytes


def _real_sqlite_bytes(tmp_path: Path) -> bytes:
    db_path = tmp_path / "_scratch.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.commit()
    conn.close()
    return db_path.read_bytes()


def test_real_sqlite_header_is_flagged(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write_bytes(repo, "data/prod.sqlite", _real_sqlite_bytes(tmp_path))
    commit_all(repo, "add sqlite")
    findings = find_committed_db_files(repo)
    assert len(findings) == 1
    assert findings[0].path == "data/prod.sqlite"
    assert findings[0].kind == "sqlite"
    assert findings[0].still_in_working_tree is True


def test_plain_text_with_sqlite_extension_is_not_flagged(tmp_path: Path) -> None:
    """The ".sqlite file that's actually plain text" edge case -- must
    check the real 16-byte magic header, not just the extension, and must
    not crash trying to read binary-shaped content as text."""
    repo = init_repo(tmp_path / "r")
    write(repo, "notes.sqlite", "this is just a text file, not a real db\n")
    commit_all(repo, "add fake sqlite")
    assert find_committed_db_files(repo) == []


def test_real_pg_dump_is_flagged_as_a_dump(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "backup.sql", """--
-- PostgreSQL database dump
--
COPY public.users (id, email) FROM stdin;
1\talice@example.com
\\.
""")
    commit_all(repo, "add dump")
    findings = find_committed_db_files(repo)
    assert len(findings) == 1
    assert findings[0].kind == "sql_dump"


def test_migration_inserting_seed_data_is_not_a_dump(tmp_path: Path) -> None:
    """A plain migration file that happens to contain INSERT statements
    (seeding reference data) must NOT be conflated with a real pg_dump/
    mysqldump output -- the precise, content-signature-based distinction
    this module commits to."""
    repo = init_repo(tmp_path / "r")
    write(repo, "migrations/0003_seed_roles.sql", """
INSERT INTO roles (name) VALUES ('admin');
INSERT INTO roles (name) VALUES ('member');
""")
    commit_all(repo, "seed migration")
    assert find_committed_db_files(repo) == []


def test_file_removed_from_working_tree_still_found_in_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write_bytes(repo, "legacy.sqlite", _real_sqlite_bytes(tmp_path))
    commit_all(repo, "add legacy sqlite (mistake)")
    (repo / "legacy.sqlite").unlink()
    commit_all(repo, "remove legacy sqlite")
    findings = find_committed_db_files(repo)
    assert len(findings) == 1
    assert findings[0].path == "legacy.sqlite"
    assert findings[0].still_in_working_tree is False


def test_empty_repo_returns_no_findings(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    assert find_committed_db_files(repo) == []
