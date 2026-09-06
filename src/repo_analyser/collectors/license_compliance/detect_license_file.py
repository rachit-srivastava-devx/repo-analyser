"""Repo-root LICENSE file detection. Precedence order is the literal spec:
LICENSE, LICENSE.md, LICENSE.txt, COPYING -- first match (case-insensitive
filename) wins, mirroring detect_primary_type's "checked in order" shape.
"""
from __future__ import annotations

from pathlib import Path

LICENSE_FILENAME_PRECEDENCE = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


def find_license_file(repo: Path) -> Path | None:
    """Return the highest-precedence LICENSE-like file at repo root, or None.

    Filename matching is case-insensitive (e.g. "license.md" matches
    "LICENSE.md"). Directories with a matching name are not files and are
    skipped deliberately.
    """
    try:
        entries = list(repo.iterdir())
    except OSError:
        return None
    for candidate in LICENSE_FILENAME_PRECEDENCE:
        for entry in entries:
            if entry.is_file() and entry.name.lower() == candidate.lower():
                return entry
    return None


def read_license_text(path: Path) -> str:
    """Defensive read: unreadable or binary-garbage files yield "" rather
    than raising, matching this codebase's fail-loud-only-on-real-tool-
    failures rule -- a LICENSE file is user content, not a tool invocation.
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
