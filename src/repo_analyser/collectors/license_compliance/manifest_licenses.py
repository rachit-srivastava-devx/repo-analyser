"""Aggregates self-declared license extraction across every recognized
manifest type. See manifest_json_licenses.py and manifest_toml_licenses.py
for the per-manifest readers.
"""
from __future__ import annotations

from pathlib import Path

from .manifest_json_licenses import license_from_composer_json, license_from_package_json
from .manifest_toml_licenses import license_from_cargo_toml, license_from_pyproject_toml


def collect_manifest_declared_licenses(repo: Path) -> list[str]:
    """All self-declared license strings found across every recognized
    manifest in repo (a repo can ship more than one manifest at once)."""
    extractors = (
        license_from_package_json,
        license_from_composer_json,
        license_from_pyproject_toml,
        license_from_cargo_toml,
    )
    return [result for extractor in extractors if (result := extractor(repo))]
