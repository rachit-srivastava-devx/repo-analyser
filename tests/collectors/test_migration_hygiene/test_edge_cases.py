from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.analyze import analyze_repo
from repo_analyser.collectors.migration_hygiene.discovery import discover_migrations

from ._migration_hygiene_helpers import commit_all, init_repo, write


def test_empty_repo_no_migrations_dir_at_all(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    result = analyze_repo(repo)
    assert result.migration_convention == "none"
    assert result.migration_file_count == 0
    assert result.skip_reason == "no migration directory or file convention detected"


def test_migrations_dir_present_but_empty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (repo / "app" / "migrations").mkdir(parents=True)
    write(repo, "app/migrations/.gitkeep", "")
    commit_all(repo, "init")
    result = analyze_repo(repo)
    assert result.migration_convention == "none"
    assert "empty" in result.skip_reason


def test_unrecognized_convention_reports_none_not_a_guess(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "db/schema.rb", "# Rails ActiveRecord schema -- not a supported convention\n")
    commit_all(repo, "init")
    result = analyze_repo(repo)
    assert result.migration_convention == "none"
    assert result.skip_reason == "no migration directory or file convention detected"


def test_huge_migration_count_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    from ._migration_hygiene_helpers import DJANGO_CREATE_MODEL
    for i in range(300):
        write(repo, f"app/migrations/{i:04d}_step.py", DJANGO_CREATE_MODEL.replace("User", f"Model{i}"))
    commit_all(repo, "huge migration set")
    result = analyze_repo(repo)
    assert result.migration_convention == "django"
    assert result.migration_file_count == 300
    assert result.reversible_count == 300


def test_symlink_to_missing_target_is_ignored(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (repo / "app" / "migrations").mkdir(parents=True)
    broken_link = repo / "app" / "migrations" / "0001_ghost.py"
    broken_link.symlink_to(repo / "does_not_exist.py")
    result = discover_migrations(repo)
    assert result.django_files == []
