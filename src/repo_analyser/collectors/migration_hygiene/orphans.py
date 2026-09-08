"""Duplicate migration detection, convention-agnostic (Django orphan
detection lives in django_orphans.py -- split to keep both under the
~80-line convention, AGENTS.md §4).

Duplicate: two files with byte-identical content (sha256, same technique
as exact_duplicates.py -- docs/METHODOLOGY.md's "two tools measuring the
same thing" rule doesn't apply here since exact_duplicates.py scans the
whole repo for *any* duplicate file, not specifically migrations; this is
a narrower, migration-specific view of the same primitive), OR the same
leading migration *number* used by two different files (a real, distinct
failure mode: two developers independently created "0007_*.py" on
separate branches, both merged).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_LEADING_NUMBER_RE = re.compile(r"^(\d+)")


def find_duplicate_files(paths: list[Path]) -> list[str]:
    """Byte-identical migration files -- one "=="-joined group label
    (all members, not just the first two) per set of identical files."""
    by_hash: dict[str, list[Path]] = {}
    for p in paths:
        try:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue  # unreadable file is reported elsewhere as reversibility "unknown"
        by_hash.setdefault(digest, []).append(p)
    return [
        "==".join(sorted(m.name for m in group))
        for group in by_hash.values() if len(group) > 1
    ]


def find_duplicate_numbers(paths: list[Path]) -> list[str]:
    """Two files sharing the same leading migration number (e.g. two
    "0007_*.py" files) -- the "same logical migration applied twice"
    signal, distinct from byte-identical content."""
    by_number: dict[str, list[Path]] = {}
    for p in paths:
        m = _LEADING_NUMBER_RE.match(p.stem)
        if m:
            by_number.setdefault(m.group(1), []).append(p)
    return [
        "==".join(sorted(m.name for m in group))
        for group in by_number.values() if len(group) > 1
    ]
