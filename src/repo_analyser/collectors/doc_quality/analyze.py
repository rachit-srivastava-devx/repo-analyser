"""Per-repo orchestration: combines the doc-comment-coverage signal (which
submodule runs depends on the repo's dominant language) with the
independently-computed changelog-discipline signal. See doc_comment_python.py
/ doc_comment_js.py for the coverage half and changelog_parse.py /
changelog_staleness.py for the changelog half -- neither half's result
depends on the other, and a skip on one is never allowed to blank out the
other (see tests/collectors/test_doc_quality/test_analyze_repo.py's
go/rust cases)."""
from __future__ import annotations

from pathlib import Path

from ...core.lang import detect_repo_language
from .changelog_parse import _changelog_last_entry
from .changelog_staleness import _changelog_staleness, latest_tag_and_date
from .doc_comment_js import _js_doc_comment_signal
from .doc_comment_python import _python_doc_coverage
from .models import DocQualityResult


def _doc_comment_signal(repo: Path, lang: str) -> tuple[float, str, str]:
    if lang == "python":
        return _python_doc_coverage(repo)
    if lang == "javascript":
        return _js_doc_comment_signal(repo)
    if lang in ("go", "rust"):
        return 0.0, "", "no keyless scriptable doc-coverage-percentage tool for this language yet"
    return 0.0, "", f"no doc-comment coverage signal wired for language '{lang}'"


def analyze_repo(repo: Path) -> DocQualityResult:
    lang = detect_repo_language(repo)
    coverage_pct, tool, skip_reason = _doc_comment_signal(repo, lang)

    has_changelog, last_entry_date = _changelog_last_entry(repo)
    tag_info = latest_tag_and_date(repo)
    staleness = _changelog_staleness(last_entry_date, tag_info[1] if tag_info else None)

    return DocQualityResult(
        repo=repo.name,
        doc_comment_coverage_pct=coverage_pct,
        doc_comment_tool=tool,
        has_changelog=has_changelog,
        changelog_last_entry_date=last_entry_date,
        changelog_stale_vs_latest_tag=staleness,
        skip_reason=skip_reason,
    )
