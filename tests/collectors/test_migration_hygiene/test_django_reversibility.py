from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.reversibility import classify_django

from ._migration_hygiene_helpers import (
    DJANGO_CREATE_MODEL,
    DJANGO_RUNPYTHON_NO_REVERSE,
    DJANGO_RUNPYTHON_WITH_REVERSE,
    write,
)


def test_auto_reversible_ops_only(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0001_initial.py", DJANGO_CREATE_MODEL)
    assert classify_django(p) == "reversible"


def test_runpython_without_reverse_is_irreversible(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0002_data.py", DJANGO_RUNPYTHON_NO_REVERSE)
    assert classify_django(p) == "irreversible"


def test_runpython_with_reverse_is_reversible(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0002_data.py", DJANGO_RUNPYTHON_WITH_REVERSE)
    assert classify_django(p) == "reversible"


def test_runpython_noop_reverse_is_reversible(tmp_path: Path) -> None:
    """migrations.RunPython.noop as the reverse_code arg is a real,
    common Django idiom for "there's nothing to undo" -- not a None
    constant, so it must count as a supplied reverse, not a missing one."""
    content = """from django.db import migrations

def forwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = []
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
"""
    p = write(tmp_path, "app/migrations/0001_seed.py", content)
    assert classify_django(p) == "reversible"


def test_malformed_python_is_unknown(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0003_broken.py", "this is not ( valid python")
    assert classify_django(p) == "unknown"


def test_unreadable_binary_is_unknown(tmp_path: Path) -> None:
    p = tmp_path / "app" / "migrations" / "0004_binary.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe\x00\x01not-utf8")
    assert classify_django(p) == "unknown"


def test_unicode_content_reversible(tmp_path: Path) -> None:
    content = DJANGO_CREATE_MODEL.replace("User", "Utilisateur_éàü")
    p = write(tmp_path, "app/migrations/0001_unicode.py", content)
    assert classify_django(p) == "reversible"


def test_runsql_without_reverse_sql_is_irreversible(tmp_path: Path) -> None:
    content = """from django.db import migrations

class Migration(migrations.Migration):
    dependencies = []
    operations = [migrations.RunSQL("DROP TABLE legacy;")]
"""
    p = write(tmp_path, "app/migrations/0002_raw_sql.py", content)
    assert classify_django(p) == "irreversible"


def test_runsql_with_reverse_sql_kwarg_is_reversible(tmp_path: Path) -> None:
    """reverse_sql supplied as a keyword argument (not positionally) must
    still be recognized -- _has_reverse checks keywords before positional
    args."""
    content = """from django.db import migrations

class Migration(migrations.Migration):
    dependencies = []
    operations = [
        migrations.RunSQL("DROP TABLE legacy;", reverse_sql="CREATE TABLE legacy (id INT);"),
    ]
"""
    p = write(tmp_path, "app/migrations/0002_raw_sql.py", content)
    assert classify_django(p) == "reversible"


def test_runpython_reverse_code_kwarg_none_is_irreversible(tmp_path: Path) -> None:
    """An explicit reverse_code=None keyword is the same as omitting it --
    must not be mistaken for "a reverse was supplied"."""
    content = """from django.db import migrations

def forwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = []
    operations = [migrations.RunPython(forwards, reverse_code=None)]
"""
    p = write(tmp_path, "app/migrations/0002_data.py", content)
    assert classify_django(p) == "irreversible"
