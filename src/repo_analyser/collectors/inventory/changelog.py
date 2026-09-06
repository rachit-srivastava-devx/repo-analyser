"""Changelog & release-note discipline (docs/checklist-by-repo-type/
single-repo.md, "Changelog & release note discipline"): does this repo keep
a human-curated changelog, and if so, how stale is it relative to its most
recent tagged release?

Deliberately not a full changelog-format parser -- only looks for the first
(assumed most recent, reverse-chronological) markdown header line carrying a
YYYY-MM-DD date: "## [1.2.3] - 2024-01-15" (Keep a Changelog), "## v1.2.3
(2024-01-15)", or any bare date on a H1-H3 header line. A changelog with no
dated entry at all (this repo's own uses undated "## 0.2.0 -- ..." headers)
is real and common, not a bug -- treat it as unknown (None), never 0."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .tags import latest_tag_date

CHANGELOG_NAMES = ("CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG", "HISTORY.md")
_HEADER_RE = re.compile(r"^#{1,3}\s.*$", re.MULTILINE)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class ChangelogSignals:
    changelog_present: bool
    changelog_last_entry_date: str | None
    latest_tag_date: str | None
    changelog_staleness_days: int | None


def _find_changelog(repo: Path) -> Path | None:
    """Case-insensitive match against CHANGELOG_NAMES, repo root only."""
    try:
        entries = {p.name.lower(): p for p in repo.iterdir() if p.is_file()}
    except OSError:
        return None
    for name in CHANGELOG_NAMES:
        hit = entries.get(name.lower())
        if hit is not None:
            return hit
    return None


def _latest_dated_header(text: str) -> date | None:
    """First header line (top of file) carrying a real YYYY-MM-DD date;
    a date-shaped-but-invalid match (e.g. month 13) is skipped, not fatal,
    in favor of the next candidate header."""
    for header in _HEADER_RE.findall(text):
        m = _DATE_RE.search(header)
        if not m:
            continue
        try:
            return datetime.strptime(m.group(), "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def collect_changelog_signals(repo: Path) -> ChangelogSignals:
    changelog_path = _find_changelog(repo)
    entry_date: date | None = None
    if changelog_path is not None:
        try:
            entry_date = _latest_dated_header(changelog_path.read_text(errors="replace"))
        except OSError:
            entry_date = None

    tag_date = latest_tag_date(repo)
    staleness = (tag_date - entry_date).days if entry_date is not None and tag_date is not None else None

    return ChangelogSignals(
        changelog_present=changelog_path is not None,
        changelog_last_entry_date=entry_date.isoformat() if entry_date else None,
        latest_tag_date=tag_date.isoformat() if tag_date else None,
        changelog_staleness_days=staleness,
    )
