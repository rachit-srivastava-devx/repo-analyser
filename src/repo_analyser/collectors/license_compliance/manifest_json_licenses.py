"""Self-declared license extraction from JSON manifests. Defensive: malformed
JSON yields no result rather than raising, mirroring (not importing -- no
cross-collector internal imports) fileio.read_json's "malformed -> empty"
contract in the sibling repo_type collector.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_json_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def license_from_package_json(repo: Path) -> str | None:
    """"license" as a plain string, or the older {"type": "..."} object form."""
    field = _read_json_dict(repo / "package.json").get("license")
    if isinstance(field, str) and field.strip():
        return field.strip()
    if isinstance(field, dict) and isinstance(field.get("type"), str) and field["type"].strip():
        return str(field["type"]).strip()
    return None


def license_from_composer_json(repo: Path) -> str | None:
    """"license" as a plain string, or an array of SPDX ids (dual-licensed)."""
    field = _read_json_dict(repo / "composer.json").get("license")
    if isinstance(field, str) and field.strip():
        return field.strip()
    if isinstance(field, list):
        names = [x.strip() for x in field if isinstance(x, str) and x.strip()]
        return " OR ".join(names) if names else None
    return None
