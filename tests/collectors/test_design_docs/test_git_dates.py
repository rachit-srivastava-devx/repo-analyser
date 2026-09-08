from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.git_dates import doc_last_commit_epoch

from ._design_docs_helpers import commit_all, init_repo, write


def test_doc_last_commit_epoch_exact_case_match(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/ARCHITECTURE.md", "arch doc")
    commit_all(repo, "add arch doc")

    assert doc_last_commit_epoch(repo, "docs/ARCHITECTURE.md") is not None


def test_doc_last_commit_epoch_falls_back_to_case_insensitive_pathspec(tmp_path: Path) -> None:
    """Regression: git's own `git log -- <path>` pathspec matching is always
    case-sensitive, independent of the host filesystem's own case-folding.
    A file genuinely tracked as "docs/ARCHITECTURE.md" queried under the
    wrong-case candidate spelling "docs/architecture.md" used to come back
    with no history at all and get miscounted as untracked
    (hld_untracked_count) even though the file is tracked fine. Fixed via a
    `:(icase)` pathspec retry on the empty-result path. This test exercises
    the git-level fallback directly and is not filesystem-case-folding
    dependent -- it passes the same way on a case-sensitive Linux CI runner
    and on macOS's case-insensitive default."""
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/ARCHITECTURE.md", "arch doc")
    commit_all(repo, "add arch doc")

    assert doc_last_commit_epoch(repo, "docs/architecture.md") is not None


def test_doc_last_commit_epoch_none_for_genuinely_untracked_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hi")
    commit_all(repo, "init")
    write(repo, "docs/design.md", "uncommitted")

    assert doc_last_commit_epoch(repo, "docs/design.md") is None
