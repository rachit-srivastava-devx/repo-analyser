"""Changelog discipline, presence + last-entry-date half:
  - has_changelog: CHANGELOG.md or HISTORY.md at repo root (case-
    insensitive filename match; deliberately not widened to other
    extensions/names the ROADMAP entry didn't ask for).
  - changelog_last_entry_date: heuristic, stated plainly -- scans the
    file's Markdown ATX headings (`#` through `####`) top-to-bottom for the
    first one containing an ISO-8601 date (`YYYY-MM-DD`), skipping heading-
    only entries with no date at all (a "## [Unreleased]" placeholder,
    universal in Keep-a-Changelog-style files, is not yet a real dated
    release). A changelog using a different structure entirely (a flat
    text list, RST underline headings, a version with no date anywhere)
    reports "" here -- a real, named limitation of this heuristic, not a
    fabricated date. See changelog_staleness.py for the tag-comparison
    half."""
from __future__ import annotations

from pathlib import Path

from .models import CHANGELOG_FILENAMES, CHANGELOG_HEADING_RE, ISO_DATE_RE


def _find_changelog(repo: Path) -> Path | None:
    for p in repo.iterdir():
        if p.is_file() and p.name.lower() in CHANGELOG_FILENAMES:
            return p
    return None


def parse_changelog_last_entry_date(text: str) -> str:
    """See module docstring's "changelog_last_entry_date" heuristic note.
    "" if no heading in the file contains a date."""
    for m in CHANGELOG_HEADING_RE.finditer(text):
        date_m = ISO_DATE_RE.search(m.group(1))
        if date_m:
            return date_m.group(0)
    return ""


def _changelog_last_entry(repo: Path) -> tuple[bool, str]:
    """Returns (has_changelog, last_entry_date)."""
    changelog = _find_changelog(repo)
    if changelog is None:
        return False, ""
    try:
        text = changelog.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True, ""
    return True, parse_changelog_last_entry_date(text)
