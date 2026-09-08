from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.adr_status_git import detect_status, modified_after_acceptance
from repo_analyser.collectors.design_docs.git_dates import commit_hashes_touching

from ._design_docs_helpers import commit_all, git_mv, init_repo, write


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


def test_modified_after_acceptance_true_across_a_rename(tmp_path: Path) -> None:
    """Regression for the `--follow`+`--reverse` git quirk: combining the
    two silently breaks rename-following, truncating the returned history
    to only the commits since the file's CURRENT path and losing the
    pre-rename accept commit entirely. This exact 4-commit shape (draft,
    accept, pure rename, real post-acceptance edit under the new name)
    reproduced the bug directly -- `commit_hashes_touching` used to return
    only the last commit here, and modified_after_acceptance reported "no"
    for an ADR that genuinely was edited after acceptance. Both the
    corrected commit list and the corrected final verdict are asserted."""
    repo = init_repo(tmp_path / "r")
    old_rel = "docs/adr/0004-orig-name.md"
    new_rel = "docs/adr/0004-renamed.md"
    write(repo, old_rel, "# ADR\n\n## Status\n\nProposed\n")
    commit_all(repo, "draft ADR")
    write(repo, old_rel, "# ADR\n\n## Status\n\nAccepted\n")
    commit_all(repo, "accept ADR")
    git_mv(repo, old_rel, new_rel)
    commit_all(repo, "rename ADR file")
    write(repo, new_rel, "# ADR\n\n## Status\n\nAccepted\n\nClarified after rename.\n")
    commit_all(repo, "real edit after rename")

    commits = commit_hashes_touching(repo, new_rel)
    assert len(commits) == 4, (
        f"expected all 4 commits across the rename, got {len(commits)}: {commits}"
    )
    assert modified_after_acceptance(repo, new_rel) == "yes"


def test_modified_after_acceptance_unknown_for_untracked_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hi")
    commit_all(repo, "init")
    rel = "docs/adr/0003-untracked.md"
    write(repo, rel, "# Untracked\n\n## Status\n\nAccepted\n")
    # Never committed.

    assert modified_after_acceptance(repo, rel) == "unknown"
