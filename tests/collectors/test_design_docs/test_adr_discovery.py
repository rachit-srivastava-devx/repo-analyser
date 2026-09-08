from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.adr_discovery import find_adr_dirs, find_adr_files

from ._design_docs_helpers import init_repo, write


def test_no_adr_dir(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hi")
    assert find_adr_dirs(repo) == []
    assert find_adr_files(repo, []) == []


def test_adr_dir_with_no_adrs(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (repo / "docs" / "adr").mkdir(parents=True)
    dirs = find_adr_dirs(repo)
    assert dirs == ["docs/adr"]
    assert find_adr_files(repo, dirs) == []


def test_finds_conventional_and_generic_adr_filenames(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/adr/0001-use-postgres.md", "adr 1")
    write(repo, "docs/adr/not-an-adr.md", "should not match")
    write(repo, "docs/adr/0002-use-kafka.md", "adr 2")
    dirs = find_adr_dirs(repo)
    files = find_adr_files(repo, dirs)
    assert [p.name for p in files] == ["0001-use-postgres.md", "0002-use-kafka.md"]


def test_multiple_adr_dir_candidates_all_scanned(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/adr/0001-a.md", "a")
    write(repo, "adr/0002-b.md", "b")
    dirs = find_adr_dirs(repo)
    assert dirs == ["adr", "docs/adr"]
    files = find_adr_files(repo, dirs)
    assert len(files) == 2


def test_huge_adr_count_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(500):
        write(repo, f"docs/adr/{i:04d}-decision.md", f"# {i}\n\nStatus: Accepted\n")
    dirs = find_adr_dirs(repo)
    files = find_adr_files(repo, dirs)
    assert len(files) == 500
