"""Finds ADR directories and, within them, ADR files. Non-recursive per
directory (ADRs conventionally live flat in one directory -- this repo's
own docs/adr/ included) rather than a full tree walk; a nested ADR
directory structure is out of scope, named in docs/METHODOLOGY.md's
known-limitations entry rather than silently unsupported."""
from __future__ import annotations

from pathlib import Path

from .models import ADR_DIR_CANDIDATES, ADR_FILENAME_RE


def find_adr_dirs(repo: Path) -> list[str]:
    """Every ADR_DIR_CANDIDATES entry that exists as a directory, sorted."""
    return sorted(rel for rel in ADR_DIR_CANDIDATES if (repo / rel).is_dir())


def find_adr_files(repo: Path, adr_dirs: list[str]) -> list[Path]:
    """ADR-shaped files (NNNN-*.md) across every discovered ADR dir,
    deduplicated by resolved path (guards the edge case of one candidate
    dir being a symlink alias of another) and sorted for deterministic
    output."""
    seen: dict[Path, Path] = {}
    for rel in adr_dirs:
        d = repo / rel
        for p in sorted(d.iterdir()):
            if p.is_file() and ADR_FILENAME_RE.match(p.name):
                seen.setdefault(p.resolve(), p)
    return sorted(seen.values(), key=lambda p: str(p))
