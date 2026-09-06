"""Shared test-fixture builders for agent_skill_quality's test package."""
from __future__ import annotations

import subprocess
from pathlib import Path


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path
