from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.pii import find_pii_columns

from ._migration_hygiene_helpers import write


def test_sql_create_table_columns(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/001_create.up.sql", """CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255),
  ssn VARCHAR(11),
  full_name VARCHAR(100)
);
""")
    matches = find_pii_columns(p)
    names = [m.split(":")[-1] for m in matches]
    assert "email" in names
    assert "ssn" in names
    assert "full_name" not in names  # not a PII keyword -- must not false-positive


def test_sql_add_column(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/002_add.up.sql", "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);")
    matches = find_pii_columns(p)
    assert any("phone_number" in m for m in matches)


def test_django_migration_field_tuple(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0001_initial.py", """from django.db import migrations, models

class Migration(migrations.Migration):
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("email", models.EmailField()),
                ("credit_card", models.CharField(max_length=20)),
            ],
        ),
    ]
""")
    matches = find_pii_columns(p)
    names = {m.split(":")[-1] for m in matches}
    assert names == {"email", "credit_card"}


def test_django_addfield_name_kwarg(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0002_add.py", """from django.db import migrations, models

class Migration(migrations.Migration):
    operations = [
        migrations.AddField(model_name="user", name="date_of_birth", field=models.DateField()),
    ]
""")
    matches = find_pii_columns(p)
    assert any("date_of_birth" in m for m in matches)


def test_sqlalchemy_column(tmp_path: Path) -> None:
    p = write(tmp_path, "alembic/versions/abc.py", """def upgrade():
    op.add_column("users", sa.Column("ip_address", sa.String()))
""")
    matches = find_pii_columns(p)
    assert any("ip_address" in m for m in matches)


def test_no_pii_columns_returns_empty(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/001.up.sql", "CREATE TABLE widgets (id SERIAL, color VARCHAR(20));")
    assert find_pii_columns(p) == []


def test_unreadable_file_returns_empty_not_crash(tmp_path: Path) -> None:
    p = tmp_path / "migrations" / "broken.up.sql"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe\x00bad")
    assert find_pii_columns(p) == []


def test_unicode_column_content_handled(tmp_path: Path) -> None:
    p = write(tmp_path, "migrations/001.up.sql", 'CREATE TABLE t (id SERIAL, email VARCHAR(255)); -- clientèle données')
    matches = find_pii_columns(p)
    assert any("email" in m for m in matches)
