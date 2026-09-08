"""Shared cell-text normalization used by signals that read a cell's
source (secrets.py needs this; outputs.py doesn't)."""
from __future__ import annotations


def cell_source_text(cell: dict) -> str:
    """nbformat's `source` field is either one string or a list of
    strings (typically one per line); normalize to a single string so a
    regex scan sees a cell's full text regardless of which form is on
    disk."""
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return source if isinstance(source, str) else ""
