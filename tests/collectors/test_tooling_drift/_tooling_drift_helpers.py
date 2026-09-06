"""Shared test-fixture builder for tooling_drift's test package."""
from __future__ import annotations

from pathlib import Path


def _mkrepo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    return repo
