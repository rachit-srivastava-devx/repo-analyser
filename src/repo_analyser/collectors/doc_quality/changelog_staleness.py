"""Changelog discipline, staleness-vs-latest-tag half:
changelog_stale_vs_latest_tag is one of "stale" / "not_stale" / "unknown".
The repo's newest tag is picked by `git for-each-ref --sort=-creatordate`
(creation date, NOT alphabetical/semver-string sort of tag names, which
breaks the moment a repo has both "v9.0.0" and "v10.0.0") -- its own
`creatordate` is the tag object's timestamp for an annotated tag, or the
pointed-at commit's committer date for a lightweight tag (git itself does
not separately record a lightweight tag's own ref-creation wall-clock
time, so this is git's own approximation, not this module's). "unknown"
is returned -- deliberately, not "not_stale" -- whenever the comparison
genuinely cannot be computed: zero git tags at all, no changelog file, or
a changelog whose top entry has no parseable date. Conflating "no tags"
with "not stale" would assert a fact about a comparison that was never
actually made. See changelog_parse.py for the presence + last-entry-date
half."""
from __future__ import annotations

from pathlib import Path

from ...core.util import run


def latest_tag_and_date(repo: Path) -> tuple[str, str] | None:
    """(tag_name, creation_date) for the repo's newest tag by creation date,
    or None if the repo has zero tags -- a clean, expected, zero-exit-code
    result (confirmed live), distinct from a real git failure, which raises
    ToolExecutionError via `run`'s default check=True."""
    res = run(
        ["git", "for-each-ref", "--sort=-creatordate",
         "--format=%(refname:short)\t%(creatordate:short)", "refs/tags"],
        cwd=repo,
    )
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    name, date = lines[0].split("\t", 1)
    return name, date


def _changelog_staleness(changelog_date: str, latest_tag_date: str | None) -> str:
    if latest_tag_date is None or not changelog_date:
        return "unknown"
    # Both sides are YYYY-MM-DD strings (ISO_DATE_RE / git's creatordate:short),
    # which sort lexicographically identically to chronologically.
    return "stale" if changelog_date < latest_tag_date else "not_stale"
