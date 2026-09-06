"""Shared, defensive file-reading helpers -- every read here tolerates a
missing/malformed file by returning an empty result rather than raising,
since a repo under analysis is never obligated to have valid syntax.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ...core.lang import EXCLUDE_DIR_PARTS


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def read_toml_has_table(path: Path, table: str) -> bool:
    """Cheap presence check for a top-level TOML table (e.g. "[build-system]")
    without a TOML parser dependency this codebase doesn't otherwise need --
    a plain per-line match on the table header is sufficient for "is this
    table declared at all", which is all this signal needs."""
    if not path.is_file():
        return False
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return False
    return re.search(rf"^\[{re.escape(table)}\]", text, re.MULTILINE) is not None


def read_yaml_docs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        docs = list(yaml.safe_load_all(path.read_text()))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return []
    return [d for d in docs if isinstance(d, dict)]


def tracked_files(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*")
            if p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)]


def immediate_subdirs(repo: Path) -> list[Path]:
    return [p for p in repo.iterdir() if p.is_dir() and p.name not in EXCLUDE_DIR_PARTS and p.name != ".git"]
