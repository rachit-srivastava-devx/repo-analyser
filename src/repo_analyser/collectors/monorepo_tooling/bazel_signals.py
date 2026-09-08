"""Signal 3: Bazel/Buck2. Presence is decided by either a workspace-root
marker file (WORKSPACE/WORKSPACE.bazel/MODULE.bazel for Bazel,
.buckconfig for Buck2) OR a nonzero count of that tool's BUILD-file naming
convention found anywhere in the tree -- a repo mid-migration to bzlmod
(MODULE.bazel only, no WORKSPACE) or one with BUILD files but no root
marker (an unusual but real shape) still counts.

No Starlark parsing of BUILD-file contents: presence/count only, per the
package docstring's stated scope. This means a BUILD file that happens to
share the filename with unrelated content (e.g. a project's own
hand-rolled "BUILD" instructions file, or a generated artifact) is
indistinguishable from a real Bazel BUILD file here -- a known, stated
limitation this collector cannot resolve without parsing file content,
which is explicitly out of scope."""
from __future__ import annotations

from pathlib import Path

from .patterns import (
    BAZEL_BUILD_FILENAMES,
    BAZEL_WORKSPACE_FILENAMES,
    BUCK_BUILD_FILENAME,
    BUCK_CONFIG_FILENAME,
)


def analyze_bazel(repo: Path, file_counts: dict[str, int]) -> tuple[bool, str, int]:
    """Returns (present, workspace_markers_found, build_file_count)."""
    markers = [name for name in BAZEL_WORKSPACE_FILENAMES if (repo / name).is_file()]
    build_count = sum(file_counts.get(name, 0) for name in BAZEL_BUILD_FILENAMES)
    present = bool(markers) or build_count > 0
    return present, ";".join(markers), build_count


def analyze_buck(repo: Path, file_counts: dict[str, int]) -> tuple[bool, int]:
    """Returns (present, build_file_count)."""
    buck_count = file_counts.get(BUCK_BUILD_FILENAME, 0)
    present = (repo / BUCK_CONFIG_FILENAME).is_file() or buck_count > 0
    return present, buck_count
