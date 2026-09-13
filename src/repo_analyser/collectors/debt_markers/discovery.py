"""Which files this collector scans: `git ls-files` (the index), same
"tracked files, not a disk walk" source of truth as codeowners_health/
fileio.py -- an untracked/gitignored file was never meant to be reviewed as
part of this repo's debt backlog, and scoping to the index also means this
collector never has to reinvent core.lang.EXCLUDE_DIR_PARTS itself.

Binary/non-UTF8 detection is a deliberate hard skip, not `errors="ignore"`
decoding: unlike a source file with one stray non-UTF8 byte in a comment
(flag_debt/discovery.py's read_text case), a genuinely binary file decoded
with replacement bytes can manufacture spurious marker matches out of
garbage bytes that happen to look like ASCII -- worse than finding nothing.
"""
from __future__ import annotations

from pathlib import Path

from ...core.util import run

# Sniff only the first chunk of a file for a NUL byte -- git's own
# `core.bigFileThreshold`-independent binary heuristic (used by `git diff`)
# does the same thing for the same reason: cheap, and a NUL this early in a
# real text file essentially never happens.
_BINARY_SNIFF_BYTES = 8000


def iter_tracked_files(repo: Path) -> list[Path]:
    """Every path git considers tracked (the index), relative to `repo`,
    resolved to absolute paths. Reflects `git add`ed-but-uncommitted files
    too, since `ls-files` reads the index, not HEAD -- consistent with
    codeowners_health's tracked_files()."""
    result = run(["git", "ls-files"], cwd=repo)
    return [repo / line for line in result.stdout.splitlines() if line]


def read_text_or_none(path: Path) -> str | None:
    """None for anything unreadable or binary-looking -- callers skip such
    files entirely rather than scanning decoded garbage (see module
    docstring). A real read failure (broken symlink, permission denied,
    deleted between ls-files and here) is the same "skip it" signal as a
    genuinely binary file, not a crash."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:_BINARY_SNIFF_BYTES]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
