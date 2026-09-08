"""Shared builder for the observability test package. analyze_repo only
ever reads the filesystem (dependency manifests + YAML), never git
history, so these are plain (non-git) directory trees -- matching
test_dead_code's own tmp_path convention.
"""
from __future__ import annotations

from pathlib import Path


def write_files(root: Path, files: dict[str, str]) -> Path:
    """files: relative-path -> content. Creates root and parent dirs as
    needed; returns root for convenient chaining."""
    root.mkdir(parents=True, exist_ok=True)
    for rel_path, content in files.items():
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root
