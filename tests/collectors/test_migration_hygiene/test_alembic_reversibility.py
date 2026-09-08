from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.alembic_reversibility import classify_alembic

from ._migration_hygiene_helpers import ALEMBIC_EMPTY_DOWNGRADE, ALEMBIC_REAL_DOWNGRADE, write


def test_real_downgrade_body_is_reversible(tmp_path: Path) -> None:
    p = write(tmp_path, "alembic/versions/abc123_add_users.py", ALEMBIC_REAL_DOWNGRADE)
    assert classify_alembic(p) == "reversible"


def test_pass_only_downgrade_is_irreversible(tmp_path: Path) -> None:
    p = write(tmp_path, "alembic/versions/def456_fake.py", ALEMBIC_EMPTY_DOWNGRADE)
    assert classify_alembic(p) == "irreversible"


def test_raise_notimplemented_downgrade_is_irreversible(tmp_path: Path) -> None:
    content = """revision = "ghi789"
down_revision = "def456"

def upgrade():
    op.drop_column("users", "email")

def downgrade():
    raise NotImplementedError("cannot restore dropped column data")
"""
    p = write(tmp_path, "alembic/versions/ghi789_drop.py", content)
    assert classify_alembic(p) == "irreversible"


def test_docstring_only_downgrade_is_irreversible(tmp_path: Path) -> None:
    content = """def upgrade():
    op.create_table("t")

def downgrade():
    \"\"\"Not implemented -- see ticket JIRA-123.\"\"\"
"""
    p = write(tmp_path, "alembic/versions/jkl012.py", content)
    assert classify_alembic(p) == "irreversible"


def test_no_downgrade_function_is_unknown(tmp_path: Path) -> None:
    content = "def upgrade():\n    op.create_table('t')\n"
    p = write(tmp_path, "alembic/versions/mno345.py", content)
    assert classify_alembic(p) == "unknown"


def test_malformed_python_is_unknown(tmp_path: Path) -> None:
    p = write(tmp_path, "alembic/versions/broken.py", "def upgrade(:\n  pass")
    assert classify_alembic(p) == "unknown"
