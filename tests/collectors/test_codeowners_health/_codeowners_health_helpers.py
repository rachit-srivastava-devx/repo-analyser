from __future__ import annotations

import subprocess
from pathlib import Path


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


def _stage_all(repo: Path) -> None:
    """Stages every file currently on disk under `repo`. This collector's
    `tracked_files` reads `git ls-files` (the index), so a fixture file
    written to disk but never `git add`ed would otherwise be invisible to
    it -- unlike repo_type's disk-crawl-based tracked_files, which needs
    no staging step at all."""
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
