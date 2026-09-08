"""Finding and parsing .ipynb files on disk. No external tool: each
notebook is read directly as JSON (nbformat's own on-disk shape -- a
top-level `cells` array; each cell has `cell_type` and `source`, and code
cells additionally have `outputs` and `execution_count`)."""
from __future__ import annotations

import json
from pathlib import Path

from .models import NOTEBOOK_EXCLUDE_DIR_PARTS


def find_notebooks(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*.ipynb")
            if p.is_file() and not any(part in NOTEBOOK_EXCLUDE_DIR_PARTS for part in p.parts)]


def read_notebook(path: Path) -> dict | None:
    """Parses one .ipynb file. Returns None for anything unusable:
    invalid JSON, non-UTF8 content, an unreadable file, valid JSON that
    isn't a top-level object, or an object with no list-typed `cells`
    key. Mirrors repo_type.py's `_read_json` shape exactly, except the
    caller here must count a None distinctly (see analyze.py) rather
    than silently treating it as empty."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
        return None
    return data
