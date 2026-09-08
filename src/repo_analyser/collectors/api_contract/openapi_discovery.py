"""Finds and content-validates OpenAPI/Swagger candidate files. Walks the
filesystem (see discovery.py's module docstring for the gitignore-inclusion
rationale shared across this whole collector)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from ...core.lang import EXCLUDE_DIR_PARTS
from .patterns import OPENAPI_DIRS, OPENAPI_FILENAMES, OPENAPI_NAME_HINT_RE, OPENAPI_SUFFIXES
from .text_io import read_text_safe


def _looks_like_openapi_dict(doc: object) -> bool:
    return isinstance(doc, dict) and "paths" in doc and ("openapi" in doc or "swagger" in doc)


def _parse_openapi_candidate(path: Path) -> tuple[bool, str | None]:
    """Returns (is_openapi, parse_error). parse_error is set only when the
    file exists and *fails* to parse -- distinct from "parsed fine but
    isn't actually an OpenAPI doc" (False, None)."""
    text, read_err = read_text_safe(path)
    if read_err:
        return False, read_err
    assert text is not None
    try:
        doc = yaml.safe_load(text) if path.suffix != ".json" else json.loads(text)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        return False, f"{path}: {e}"
    return _looks_like_openapi_dict(doc), None


def _candidate_paths(repo: Path) -> list[Path]:
    candidates: list[Path] = []
    for d in OPENAPI_DIRS:
        for name in OPENAPI_FILENAMES:
            p = repo / d / name if d else repo / name
            if p.is_file():
                candidates.append(p)
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.suffix in OPENAPI_SUFFIXES and OPENAPI_NAME_HINT_RE.search(p.name) and p not in candidates:
            candidates.append(p)
    return candidates


def find_openapi_files(repo: Path) -> tuple[list[Path], list[str]]:
    """Returns (files_confirmed_as_openapi, parse_errors). A candidate that
    parses fine but isn't actually an OpenAPI/Swagger doc is silently
    dropped (not an error) -- only a genuine parse failure is reported."""
    found: list[Path] = []
    errors: list[str] = []
    for p in _candidate_paths(repo):
        is_openapi, err = _parse_openapi_candidate(p)
        if err:
            errors.append(err)
        elif is_openapi:
            found.append(p)
    return found, errors
