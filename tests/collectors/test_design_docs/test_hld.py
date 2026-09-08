from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from repo_analyser.collectors.design_docs.hld import collect_hld_signal, find_hld_candidates

from ._design_docs_helpers import commit_all, init_repo, write


def test_no_hld_candidates_in_empty_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hello")
    commit_all(repo, "init")
    now = datetime.now(timezone.utc)

    assert find_hld_candidates(repo) == []
    signal = collect_hld_signal(repo, now)
    assert signal.has_hld is False
    assert signal.days_since_doc_touched is None
    assert signal.repo_has_commits is True


def test_zero_commit_repo_reports_no_repo_commits_not_a_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    now = datetime.now(timezone.utc)

    signal = collect_hld_signal(repo, now)
    assert signal.repo_has_commits is False
    assert signal.days_since_repo_last_commit is None
    assert signal.has_hld is False


def test_multiple_hld_candidates_all_reported(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    # Two *distinct* candidate names (not case-variants of each other --
    # macOS's default case-insensitive filesystem would otherwise collide
    # ARCHITECTURE.md and docs/architecture.md into the same file).
    write(repo, "ARCHITECTURE.md", "root arch doc")
    write(repo, "docs/design.md", "design doc")
    commit_all(repo, "add arch docs")
    now = datetime.now(timezone.utc)

    signal = collect_hld_signal(repo, now)
    assert signal.has_hld is True
    assert signal.docs_found == ["ARCHITECTURE.md", "docs/design.md"]
    assert signal.untracked_count == 0
    assert signal.days_since_doc_touched == 0


def test_untracked_hld_doc_has_no_freshness_signal(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hello")
    commit_all(repo, "init")
    # Written but never committed -- exists on the filesystem, no git history.
    write(repo, "docs/design.md", "uncommitted design doc")
    now = datetime.now(timezone.utc)

    signal = collect_hld_signal(repo, now)
    assert signal.has_hld is True
    assert signal.untracked_count == 1
    assert signal.days_since_doc_touched is None
    # The repo itself does have commits (the README one) -- that side of
    # the signal is still real and reported.
    assert signal.repo_has_commits is True
    assert signal.days_since_repo_last_commit == 0


def test_stale_hld_relative_to_repo_activity(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/ARCHITECTURE.md", "arch doc")
    commit_all(repo, "add arch doc")
    write(repo, "src/app.py", "print('hi')")
    commit_all(repo, "add app code")

    # Simulate "10 days have passed since the repo's last commit" by moving
    # the analysis clock forward rather than backdating git commits.
    now = datetime.now(timezone.utc) + timedelta(days=10)
    signal = collect_hld_signal(repo, now)
    assert signal.days_since_doc_touched == 10
    assert signal.days_since_repo_last_commit == 10
