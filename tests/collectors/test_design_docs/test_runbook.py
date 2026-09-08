from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.runbook import collect_runbook_signal

from ._design_docs_helpers import RUNBOOK_TEXT, init_repo, write


def test_no_runbook_at_all(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "# My Project\n\nJust a description.\n")
    signal = collect_runbook_signal(repo)
    assert signal.has_runbook is False
    assert signal.docs_found == []
    assert signal.keyword_categories == []


def test_dedicated_runbook_file_with_all_keyword_categories(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "RUNBOOK.md", RUNBOOK_TEXT)
    signal = collect_runbook_signal(repo)
    assert signal.has_runbook is True
    assert signal.docs_found == ["RUNBOOK.md"]
    assert signal.keyword_categories == ["deploy", "known_failure_mode", "on_call", "rollback"]


def test_readme_section_counts_as_runbook(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "# Project\n\n## Rollback\n\nRun the rollback script.\n")
    signal = collect_runbook_signal(repo)
    assert signal.has_runbook is True
    assert signal.docs_found == ["README.md#runbook-section"]
    assert "rollback" in signal.keyword_categories


def test_readme_prose_mentioning_deploy_without_a_section_header_does_not_count(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "# Project\n\nWe deploy this with GitHub Actions.\n")
    signal = collect_runbook_signal(repo)
    assert signal.has_runbook is False
