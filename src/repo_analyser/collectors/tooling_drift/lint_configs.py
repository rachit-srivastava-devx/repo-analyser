"""Per-directory / per-manifest lint-config fingerprints -- eslint
(package.json's own directory), ruff (pyproject.toml's own [tool.ruff]
table), golangci (go.mod's own directory). Each `*_display` function
reduces one manifest's sibling lint config to a short comparable string:
"missing" when absent, else a content hash -- so two sibling directories
that both have a same-named config but different rules inside still
compare unequal, not just presence-vs-absence.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import ESLINT_CONFIG_NAMES, GOLANGCI_CONFIG_NAMES


def _config_files_in(directory: Path, names: tuple[str, ...]) -> list[Path]:
    return sorted(directory / name for name in names if (directory / name).is_file())


def _dir_config_display(directory: Path, names: tuple[str, ...]) -> str:
    """"missing" when none of `names` exists in `directory`; otherwise a
    short content hash per file found, joined -- so two sibling
    directories that both have a same-named config file but with
    different rules inside still compare unequal (the checklist's own
    "...or has non-identical content for" wording, not presence-only)."""
    files = _config_files_in(directory, names)
    if not files:
        return "missing"
    parts = []
    for p in files:
        try:
            content = p.read_text()
        except (UnicodeDecodeError, OSError):
            content = "<unreadable>"
        parts.append(f"{p.name}#{hashlib.sha256(content.encode()).hexdigest()[:8]}")
    return "+".join(parts)


def eslint_display(package_json_path: Path) -> str:
    return _dir_config_display(package_json_path.parent, ESLINT_CONFIG_NAMES)


def golangci_display(go_mod_path: Path) -> str:
    return _dir_config_display(go_mod_path.parent, GOLANGCI_CONFIG_NAMES)


def _has_toml_table(text: str, table: str) -> re.Match[str] | None:
    """Same per-line "[table]" header regex as repo_type.py's own
    `_read_toml_has_table` (AGENTS.md SS4: collectors stay independent,
    reimplemented locally), returning the Match itself rather than a bool
    -- `ruff_display` below also needs the match's own *position*, to
    slice out the table's own body for content hashing, which
    repo_type.py's presence-only check never needed."""
    return re.search(rf"^\[{re.escape(table)}\]", text, re.MULTILINE)


def ruff_display(pyproject_path: Path) -> str:
    """"missing" when this pyproject.toml declares no `[tool.ruff]` table
    at all; otherwise a short hash of the table's own text span (from its
    header to the next top-level "[...]" header, or EOF) -- so two
    sibling pyproject.toml files that both declare `[tool.ruff]` but
    configure different rules still compare unequal, matching the
    eslint/golangci content-hash treatment above."""
    try:
        text = pyproject_path.read_text()
    except (UnicodeDecodeError, OSError):
        return "missing"
    m = _has_toml_table(text, "tool.ruff")
    if not m:
        return "missing"
    rest = text[m.start():]
    next_header = re.search(r"\n\[", rest[1:])
    table_text = rest[:next_header.start() + 1] if next_header else rest
    return f"tool.ruff#{hashlib.sha256(table_text.encode()).hexdigest()[:8]}"
