"""ADR status detection, and the "immutable once accepted" git-history
signal. Two separate questions, deliberately kept apart:

1. detect_status(text) -- what does this ADR's *current* content say its
   status is, right now. A windowed label-then-value search (same shape as
   api_contract's deprecation-marker/sunset-signal window): the "Status"
   label and its value are often on separate lines (a bare "## Status"
   heading followed by "Accepted" on the next line is the common MADR
   shape), so a same-line-only regex would under-detect.

2. modified_after_acceptance(...) -- for an ADR whose *current* content is
   "accepted", did any commit touch the file after the commit that first
   introduced that accepted-status text. This can only ever report a fact
   about git history, never a judgment about *what* changed -- a typo fix
   and a real status reversal look identical to this check (stated
   plainly in the package docstring and docs/METHODOLOGY.md, not
   editorialized here)."""
from __future__ import annotations

from pathlib import Path

from .git_dates import commit_hashes_touching, content_at_commit
from .models import ADR_STATUS_LABEL_RE, ADR_STATUS_VALUES, ADR_STATUS_WINDOW_LINES


def detect_status(text: str) -> str:
    """First status value found top-to-bottom, or "" when no recognizable
    status marker exists at all -- reported as such by the caller
    (adr_status_unknown_count), never guessed."""
    lines = text.splitlines()
    for m in ADR_STATUS_LABEL_RE.finditer(text):
        line_idx = text.count("\n", 0, m.start())
        hi = min(len(lines), line_idx + ADR_STATUS_WINDOW_LINES + 1)
        window = "\n".join(lines[line_idx:hi]).lower()
        for value in ADR_STATUS_VALUES:
            if value in window:
                return value
    return ""


def modified_after_acceptance(repo: Path, rel_path: str) -> str:
    """One of "yes" / "no" / "unknown" for an ADR already confirmed (by the
    caller) to currently read as accepted.

    "unknown" when the path has no git history at all (untracked/
    uncommitted -- can't compute a fact about history that doesn't exist)
    or a revision's content can't be read back (rename edge case, see
    git_dates.content_at_commit). "yes" only when a commit *after* the
    first commit whose content shows accepted-status also touched the
    file -- not merely "the file has more than one commit", since several
    commits can precede acceptance (drafting, review edits) with none
    following it."""
    commits = commit_hashes_touching(repo, rel_path)
    if not commits:
        return "unknown"

    accepted_idx: int | None = None
    for i, sha in enumerate(commits):
        content = content_at_commit(repo, sha, rel_path)
        if content is None:
            continue
        if detect_status(content) == "accepted":
            accepted_idx = i
            break

    if accepted_idx is None:
        # Current content is accepted but no historical revision this walk
        # could read ever showed it -- e.g. every revision-read failed
        # (rename chain gap), or the accepted line was only ever staged,
        # never committed as such. Distinct from "no history at all".
        return "unknown"
    return "yes" if accepted_idx < len(commits) - 1 else "no"
