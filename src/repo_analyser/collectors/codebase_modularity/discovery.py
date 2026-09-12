"""File/package walk shared by module_size.py (and, for the Python subset,
god_class.py). One bounded walk finds every recognized source file at
once, same "walk once, not N times" rationale as migration_hygiene/
discovery.py.

SOURCE_EXTENSIONS is deliberately its own constant rather than reusing
core.lang.EXT_TO_LANG: EXT_TO_LANG exists to answer "what language is the
dominant one in this repo" (detect_repo_language), so it's missing
extensions that are still unambiguously source code but rarely a repo's
*dominant* language on their own (C/C++'s `.c`/`.cpp`/`.h`/`.hpp`).
Module/package size budgets need "is this a source file worth counting",
a different question, so this list is the reasonable common set named in
the brief instead."""
from __future__ import annotations

from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb",
    ".c", ".cpp", ".h", ".hpp",
}


def iter_source_files(repo: Path) -> list[Path]:
    """Every file under `repo` with a recognized source extension, skipping
    anything under an excluded directory part. Walks once; callers filter
    further (e.g. by suffix) rather than re-walking."""
    out: list[Path] = []
    for p in repo.rglob("*"):
        if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.is_file() and p.suffix in SOURCE_EXTENSIONS:
            out.append(p)
    return out


def iter_python_files(repo: Path) -> list[Path]:
    """Python subset of iter_source_files, for god_class.py -- a separate
    function (not a filter the caller applies itself) so both callers
    agree on the same excluded-dir walk without duplicating it."""
    return [p for p in iter_source_files(repo) if p.suffix == ".py"]
