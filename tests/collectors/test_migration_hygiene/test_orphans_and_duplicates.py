from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.django_orphans import find_django_orphans
from repo_analyser.collectors.migration_hygiene.orphans import (
    find_duplicate_files,
    find_duplicate_numbers,
    find_duplicate_numbers_by_group,
)

from ._migration_hygiene_helpers import write


def test_byte_identical_files_are_duplicates(tmp_path: Path) -> None:
    a = write(tmp_path, "app/migrations/0001_a.py", "same content\n")
    b = write(tmp_path, "app/migrations/0002_b.py", "same content\n")
    c = write(tmp_path, "app/migrations/0003_c.py", "different content\n")
    dupes = find_duplicate_files([a, b, c])
    assert dupes == ["0001_a.py==0002_b.py"]


def test_unreadable_path_is_skipped_not_crashed(tmp_path: Path) -> None:
    """A path that doesn't exist (or can't be read) must not crash the
    duplicate scan -- e.g. a dangling reference from another module's
    discovery pass."""
    missing = tmp_path / "app" / "migrations" / "0001_gone.py"
    real = write(tmp_path, "app/migrations/0002_real.py", "content\n")
    assert find_duplicate_files([missing, real]) == []


def test_no_duplicates_when_all_distinct(tmp_path: Path) -> None:
    a = write(tmp_path, "app/migrations/0001_a.py", "one\n")
    b = write(tmp_path, "app/migrations/0002_b.py", "two\n")
    assert find_duplicate_files([a, b]) == []


def test_same_leading_number_is_a_duplicate(tmp_path: Path) -> None:
    a = write(tmp_path, "app/migrations/0007_add_index.py", "content one\n")
    b = write(tmp_path, "app/migrations/0007_add_column.py", "content two\n")
    dupes = find_duplicate_numbers([a, b])
    assert dupes == ["0007_add_column.py==0007_add_index.py"]


def test_multi_app_django_shared_leading_number_is_not_a_duplicate(tmp_path: Path) -> None:
    """Two independent, legitimate Django apps each starting their own
    migration numbering at 0001 (the normal case for any real multi-app
    Django project) must NOT be flagged as duplicates just because the
    unscoped, convention-agnostic find_duplicate_numbers would see two
    "0001"-prefixed files -- analyze_repo scopes this per app via
    find_duplicate_numbers_by_group, keyed the same way
    find_django_orphans already groups by app (p.parent.parent.name)."""
    blog = write(tmp_path, "blog/migrations/0001_initial.py", "dependencies = []\n")
    shop = write(tmp_path, "shop/migrations/0001_initial.py", "dependencies = []\n")
    dupes = find_duplicate_numbers_by_group(
        [blog, shop], key=lambda p: p.parent.parent.name
    )
    assert dupes == []
    # The unscoped function, called directly on the same two paths, is
    # exactly the bug being fixed here -- confirms the test would have
    # caught it if find_duplicate_numbers_by_group fell back to it.
    assert find_duplicate_numbers([blog, shop]) == ["0001_initial.py==0001_initial.py"]


def test_same_app_duplicate_still_caught_when_grouped(tmp_path: Path) -> None:
    """A genuine same-app duplicate (two files in the SAME app sharing a
    leading number) must still be flagged once grouping is applied."""
    a = write(tmp_path, "blog/migrations/0007_add_index.py", "dependencies = []\n")
    b = write(tmp_path, "blog/migrations/0007_add_column.py", "dependencies = []\n")
    other_app = write(tmp_path, "shop/migrations/0001_initial.py", "dependencies = []\n")
    dupes = find_duplicate_numbers_by_group(
        [a, b, other_app], key=lambda p: p.parent.parent.name
    )
    assert dupes == ["0007_add_column.py==0007_add_index.py"]


def test_django_orphan_dependency_not_found(tmp_path: Path) -> None:
    existing = write(tmp_path, "app/migrations/0001_initial.py", "dependencies = []\n")
    orphan = write(
        tmp_path, "app/migrations/0002_next.py",
        'dependencies = [("app", "0099_missing")]\n',
    )
    orphans = find_django_orphans([existing, orphan])
    assert orphans == ["0002_next.py->0099_missing"]


def test_django_dependency_found_is_not_an_orphan(tmp_path: Path) -> None:
    initial = write(tmp_path, "app/migrations/0001_initial.py", "dependencies = []\n")
    next_ = write(
        tmp_path, "app/migrations/0002_next.py",
        'dependencies = [("app", "0001_initial")]\n',
    )
    assert find_django_orphans([initial, next_]) == []


def test_cross_app_dependency_is_not_checked(tmp_path: Path) -> None:
    """A dependency on a different app's migration can't be resolved from
    this collector's own single-app file listing -- deliberately skipped,
    not misreported as an orphan."""
    p = write(
        tmp_path, "app/migrations/0001_initial.py",
        'dependencies = [("other_app", "0005_something")]\n',
    )
    assert find_django_orphans([p]) == []


def test_malformed_python_does_not_crash_orphan_detection(tmp_path: Path) -> None:
    p = write(tmp_path, "app/migrations/0001_broken.py", "dependencies = [ this is ( not valid")
    assert find_django_orphans([p]) == []


def test_unreadable_binary_does_not_crash_orphan_detection(tmp_path: Path) -> None:
    p = tmp_path / "app" / "migrations" / "0001_binary.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe\x00not-utf8")
    assert find_django_orphans([p]) == []


def test_non_string_dependency_tuple_element_is_skipped(tmp_path: Path) -> None:
    """A dependencies entry whose elements aren't both string literals
    (e.g. a dynamically referenced name) can't be resolved statically --
    skipped rather than crashing or misreporting."""
    p = write(tmp_path, "app/migrations/0001_dynamic.py", "dependencies = [(1, 2)]\n")
    assert find_django_orphans([p]) == []
