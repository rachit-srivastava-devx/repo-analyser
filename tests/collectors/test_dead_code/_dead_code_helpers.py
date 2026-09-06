"""Shared builder for the dead_code test package. Unlike tests/conftest.py's
git_repo()/git_portfolio(), dead_code's analyze_repo never reads git
history -- it only walks the filesystem -- so these are plain (non-git)
directory trees, matching test_lint_quality.py's own tmp_path convention.
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
