"""Single bounded tree walk shared by nx/bazel/buck signal detection --
counts occurrences of a fixed filename set anywhere under the repo,
skipping EXCLUDE_DIR_PARTS (vendor/node_modules/build-output dirs), so a
monorepo with tens of thousands of files is walked once, not once per
tool being checked for. Walks the real filesystem (like
api_contract/discovery.py, depgraph.py, duplication.py), not
`git ls-files` -- a gitignored-but-present BUILD/project.json file still
counts, matching this repo's existing convention for filesystem-walking
collectors."""
from __future__ import annotations

from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS


def count_files_by_name(repo: Path, names: frozenset[str]) -> dict[str, int]:
    counts = {name: 0 for name in names}
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.name in counts:
            counts[p.name] += 1
    return counts
