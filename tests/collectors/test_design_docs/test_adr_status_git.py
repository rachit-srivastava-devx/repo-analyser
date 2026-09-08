from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.adr_status_git import detect_status, modified_after_acceptance

from ._design_docs_helpers import commit_all, init_repo, write


def test_detect_status_inline_and_windowed() -> None:
    assert detect_status("Status: Accepted\n") == "accepted"
    assert detect_status("## Status\n\nAccepted\n") == "accepted"
    assert detect_status("**Status:** Proposed\n") == "proposed"


def test_detect_status_unknown_when_no_marker() -> None:
    assert detect_status("Just some prose about a decision.") == ""


def test_modified_after_acceptance_fires_for_a_real_post_acceptance_edit(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    rel = "docs/adr/0001-use-postgres.md"
    write(repo, rel, "# Use Postgres\n\n## Status\n\nProposed\n")
    commit_all(repo, "draft ADR")
    write(repo, rel, "# Use Postgres\n\n## Status\n\nAccepted\n")
    commit_all(repo, "accept ADR")
    # A real edit landing AFTER acceptance -- the exact scenario this
    # signal exists to catch.
    write(repo, rel, "# Use Postgres\n\n## Status\n\nAccepted\n\nClarified rationale.\n")
    commit_all(repo, "tweak accepted ADR")

    assert modified_after_acceptance(repo, rel) == "yes"


def test_modified_after_acceptance_no_when_acceptance_is_the_latest_commit(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    rel = "docs/adr/0002-use-kafka.md"
    write(repo, rel, "# Use Kafka\n\n## Status\n\nProposed\n")
    commit_all(repo, "draft ADR")
    write(repo, rel, "# Use Kafka\n\n## Status\n\nAccepted\n")
    commit_all(repo, "accept ADR")

    assert modified_after_acceptance(repo, rel) == "no"


def test_modified_after_acceptance_unknown_for_untracked_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hi")
    commit_all(repo, "init")
    rel = "docs/adr/0003-untracked.md"
    write(repo, rel, "# Untracked\n\n## Status\n\nAccepted\n")
    # Never committed.

    assert modified_after_acceptance(repo, rel) == "unknown"
