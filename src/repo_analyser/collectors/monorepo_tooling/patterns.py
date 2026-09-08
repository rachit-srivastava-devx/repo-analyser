"""Detection constants for the monorepo_tooling collector: orchestrator
marker filenames and the bounded-scan target filenames used to count
BUILD/BUCK/project.json files. Kept separate from the per-tool signal
modules so each stays under the package's ~80-line convention."""
from __future__ import annotations

NX_CONFIG_FILENAME = "nx.json"
NX_PROJECT_JSON_FILENAME = "project.json"

TURBO_CONFIG_FILENAME = "turbo.json"

BAZEL_WORKSPACE_FILENAMES = ("WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel")
BAZEL_BUILD_FILENAMES = ("BUILD", "BUILD.bazel")

BUCK_CONFIG_FILENAME = ".buckconfig"
BUCK_BUILD_FILENAME = "BUCK"

PANTS_CONFIG_FILENAME = "pants.toml"

# Filenames counted in the single bounded tree walk shared by nx/bazel/buck
# signal detection (fs_scan.count_files_by_name) -- one rglob pass, not one
# per tool, so a monorepo with tens of thousands of files (AGENTS.md SS3's
# "huge" rung) is walked once regardless of how many orchestrators are
# being checked for.
SCANNED_FILENAMES = frozenset((NX_PROJECT_JSON_FILENAME, *BAZEL_BUILD_FILENAMES, BUCK_BUILD_FILENAME))
