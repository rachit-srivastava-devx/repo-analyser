"""Which files this collector scans (the 8 extensions the brief names), and
forgiving text reading for them. Kept local to this package rather than
reusing another collector's internal file-walk -- a collector's own
submodules are not a shared library (AGENTS.md's collector-package rule);
core.lang.EXCLUDE_DIR_PARTS is the actual shared primitive to build a
file-walk from.
"""
from __future__ import annotations

from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS

SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb"}


def iter_source_files(repo: Path) -> list[Path]:
    return [
        p for p in repo.rglob("*")
        if p.is_file() and p.suffix in SOURCE_EXTENSIONS
        and not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)
    ]


def read_text(path: Path) -> str:
    """errors="ignore" (not a strict try/except like flag_definitions.py's
    config-file reads) is deliberate: a source file that's UTF-8 except for
    one stray non-UTF8 byte in, say, a comment is still worth scanning for
    the rest of its content -- unlike a config file, where a decode failure
    makes the whole structured parse meaningless anyway."""
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""
