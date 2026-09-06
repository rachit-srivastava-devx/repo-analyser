"""Self-declared license extraction from TOML manifests via plain regex --
no TOML parser dependency (this repo's 3.10 floor predates stdlib tomllib).
Extends fileio.read_toml_has_table's regex-driven presence check into a
value-bearing span extraction; malformed TOML simply fails to match and
yields None rather than raising.
"""
from __future__ import annotations

import re
from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _toml_table_span(text: str, header: str) -> str:
    """Text of a top-level [header] table, up to the next top-level [...]
    header or EOF."""
    match = re.search(rf"(?m)^\[{re.escape(header)}\]\s*$", text)
    if not match:
        return ""
    rest = text[match.end():]
    next_header = re.search(r"(?m)^\[", rest)
    return rest[: next_header.start()] if next_header else rest


def _scalar_field(span: str, key: str) -> str | None:
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]*)"', span)
    return (match.group(1).strip() or None) if match else None


def _table_text_field(span: str, key: str) -> str | None:
    """key = { text = "...", ... } table form, e.g. PEP 621 [project] license."""
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*\{{[^}}]*\btext\s*=\s*"([^"]*)"', span)
    return (match.group(1).strip() or None) if match else None


def license_from_pyproject_toml(repo: Path) -> str | None:
    """PEP 621 [project] license (string or {text = "..."} table), falling
    back to the older [tool.poetry] license key."""
    text = _read_text(repo / "pyproject.toml")
    project_span = _toml_table_span(text, "project")
    found = _scalar_field(project_span, "license") or _table_text_field(project_span, "license")
    return found or _scalar_field(_toml_table_span(text, "tool.poetry"), "license")


def license_from_cargo_toml(repo: Path) -> str | None:
    """[package] license in Cargo.toml."""
    return _scalar_field(_toml_table_span(_read_text(repo / "Cargo.toml"), "package"), "license")
