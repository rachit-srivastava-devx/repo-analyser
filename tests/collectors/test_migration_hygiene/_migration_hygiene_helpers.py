"""Shared fixture-building helpers for the migration_hygiene test package.
Named per-collector (not the generic `_helpers.py`) because tests/ has no
`__init__.py` anywhere -- pytest's prepend import mode means a generic
name would collide with every other collector's identically-named helper
module in sys.modules the moment the full suite runs together (AGENTS.md
§4)."""
from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                           text=True, env=_ENV)


def init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    return repo


def write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def write_bytes(repo: Path, rel: str, data: bytes) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


DJANGO_CREATE_MODEL = """from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("email", models.EmailField()),
            ],
        ),
    ]
"""

DJANGO_RUNPYTHON_NO_REVERSE = """from django.db import migrations

def forwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [("app", "0001_initial")]
    operations = [migrations.RunPython(forwards)]
"""

DJANGO_RUNPYTHON_WITH_REVERSE = """from django.db import migrations

def forwards(apps, schema_editor):
    pass

def backwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [("app", "0001_initial")]
    operations = [migrations.RunPython(forwards, backwards)]
"""

ALEMBIC_REAL_DOWNGRADE = """revision = "abc123"
down_revision = None

def upgrade():
    op.create_table("users")

def downgrade():
    op.drop_table("users")
"""

ALEMBIC_EMPTY_DOWNGRADE = """revision = "def456"
down_revision = "abc123"

def upgrade():
    op.add_column("users", "email")

def downgrade():
    pass
"""
