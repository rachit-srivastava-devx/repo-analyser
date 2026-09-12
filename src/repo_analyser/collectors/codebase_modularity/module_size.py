"""Signal 1: module/package size budget -- language-agnostic, no external
tool, pure filesystem walk + line counting. Two deliberate, documented
thresholds matching common lint-tool conventions (ESLint's `max-lines`
default gate, SonarQube Community Edition's file-size code smell) rather
than an invented number:

- **Oversized file**: physical LOC (`len(text.splitlines())`) > 500.
- **Oversized package**: a directory containing more than 40 source files
  directly inside it (non-recursive -- a subdirectory's files don't count
  toward its parent's total; that's a separate, potentially also-oversized
  directory in its own right).

Both thresholds are strict `>`, not `>=` -- a file at exactly 500 LOC or a
directory with exactly 40 files is at the budget, not over it (kept
consistent with god_class.py's own `>` choice for the same reason)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .discovery import iter_source_files
from .patterns import SAMPLE_CAP, join_sample

OVERSIZED_FILE_LOC_THRESHOLD = 500
OVERSIZED_PACKAGE_FILE_COUNT_THRESHOLD = 40


@dataclass
class ModuleSizeFindings:
    oversized_file_count: int
    oversized_files: str
    oversized_package_count: int
    oversized_packages: str


def _line_count(path: Path) -> int | None:
    """None on a real read failure (broken symlink, permission denied) --
    such a file is skipped rather than crashing the whole walk, mirroring
    depgraph.py's file.read_text(errors="ignore") -- decoding errors are
    replaced, not raised, but a genuinely unreadable path still needs a
    distinct "skip it" signal."""
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None
    return len(text.splitlines())


def find_module_size_findings(repo: Path) -> ModuleSizeFindings:
    files = iter_source_files(repo)

    oversized_files: list[str] = []
    dir_counts: Counter[Path] = Counter()
    for f in files:
        dir_counts[f.parent] += 1
        loc = _line_count(f)
        if loc is not None and loc > OVERSIZED_FILE_LOC_THRESHOLD:
            oversized_files.append(f"{f.relative_to(repo)}({loc})")

    oversized_packages = [
        f"{'.' if d == repo else d.relative_to(repo)}({count})"
        for d, count in dir_counts.items()
        if count > OVERSIZED_PACKAGE_FILE_COUNT_THRESHOLD
    ]

    return ModuleSizeFindings(
        oversized_file_count=len(oversized_files),
        oversized_files=join_sample(sorted(oversized_files), SAMPLE_CAP),
        oversized_package_count=len(oversized_packages),
        oversized_packages=join_sample(sorted(oversized_packages), SAMPLE_CAP),
    )
