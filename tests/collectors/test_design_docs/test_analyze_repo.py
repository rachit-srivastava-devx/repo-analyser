from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.analyze import analyze_repo

from ._design_docs_helpers import (
    ADR_ACCEPTED,
    ADR_PROPOSED_NO_SECTIONS,
    RUNBOOK_TEXT,
    commit_all,
    init_repo,
    write,
    write_bytes,
)


def test_empty_repo_no_docs_at_all_reports_skip_reason(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "src/app.py", "print('hi')")
    commit_all(repo, "init")

    result = analyze_repo(repo)
    assert result.has_hld is False
    assert result.has_adr_dir is False
    assert result.has_runbook is False
    assert result.skip_reason != ""


def test_adr_dir_with_no_adrs_no_skip_reason_if_dir_exists(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (repo / "docs" / "adr").mkdir(parents=True)
    write(repo, "README.md", "hi")
    commit_all(repo, "init")

    result = analyze_repo(repo)
    assert result.has_adr_dir is True
    assert result.adr_file_count == 0
    assert result.skip_reason == ""


def test_full_success_case_with_accepted_and_proposed_adrs_and_runbook(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/ARCHITECTURE.md", "# Architecture\n\nOverview.\n")
    write(repo, "docs/adr/0001-accepted.md", ADR_ACCEPTED)
    write(repo, "docs/adr/0002-proposed.md", ADR_PROPOSED_NO_SECTIONS)
    write(repo, "RUNBOOK.md", RUNBOOK_TEXT)
    commit_all(repo, "add design docs")

    result = analyze_repo(repo)
    assert result.has_hld is True
    # On a case-insensitive filesystem (macOS/Windows default), the
    # docs/ARCHITECTURE.md and docs/architecture.md candidates both resolve
    # to this one file -- both are reported as found (see models.py's
    # docstring note on this known, documented filesystem caveat).
    assert "docs/ARCHITECTURE.md" in result.hld_docs_found.split(";")
    assert result.has_adr_dir is True
    assert result.adr_file_count == 2
    assert result.adr_malformed_count == 0
    assert result.adr_with_standard_sections_count == 1
    assert result.adr_status_accepted_count == 1
    assert result.adr_status_unknown_count == 0
    assert result.adr_reversibility_tagged_count == 1
    assert result.has_runbook is True
    assert result.runbook_keyword_category_count == 4
    assert result.skip_reason == ""


def test_malformed_adr_file_does_not_crash_and_is_counted_separately(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/adr/0001-good.md", ADR_ACCEPTED)
    write_bytes(repo, "docs/adr/0002-bad.md", b"\xff\xfe\x00garbage-not-utf8")
    commit_all(repo, "add adrs incl malformed")

    result = analyze_repo(repo)
    assert result.adr_file_count == 2
    assert result.adr_malformed_count == 1
    # The malformed file must not have been silently counted as a working
    # ADR for any content-based signal.
    assert result.adr_status_accepted_count == 1


def test_accepted_adr_with_no_git_history_reports_unknown_not_yes_or_no(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hi")
    commit_all(repo, "init")
    # Written but never committed -- accepted-looking content with zero
    # git history behind it.
    write(repo, "docs/adr/0001-uncommitted.md", ADR_ACCEPTED)

    result = analyze_repo(repo)
    assert result.adr_status_accepted_count == 1
    assert result.adr_modified_after_acceptance_count == 0
    assert result.adr_acceptance_history_unknown_count == 1


def test_huge_adr_count_across_full_analyze_repo_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    for i in range(200):
        write(repo, f"docs/adr/{i:04d}-decision.md", f"# {i}\n\nStatus: Proposed\n")
    commit_all(repo, "add many ADRs")

    result = analyze_repo(repo)
    assert result.adr_file_count == 200
    assert result.adr_status_accepted_count == 0


def test_unicode_content_in_adr_and_hld_is_handled(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "docs/ARCHITECTURE.md", "# 架构概览\n\n概述内容 émigré café ☃\n")
    write(repo, "docs/adr/0001-unicode.md", "# 決定\n\n## Status\n\nAccepted\n\n reversible\n")
    commit_all(repo, "unicode docs")

    result = analyze_repo(repo)
    assert result.has_hld is True
    assert result.adr_status_accepted_count == 1
    assert result.adr_reversibility_tagged_count == 1
