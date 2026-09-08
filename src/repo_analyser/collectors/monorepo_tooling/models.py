"""Result dataclass for the monorepo_tooling collector. See package
docstring (__init__.py) for the full contract; see patterns.py for the
detection constants used by the per-tool signal modules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MonorepoToolingResult:
    repo: str
    orchestrators_detected: str
    orchestrator_count: int
    nx_present: bool
    nx_valid_json: bool
    nx_has_configured_graph: bool
    nx_project_json_count: int
    turbo_present: bool
    turbo_valid_json: bool
    turbo_schema: str
    turbo_task_count: int
    bazel_present: bool
    bazel_workspace_markers: str
    bazel_build_file_count: int
    buck_present: bool
    buck_build_file_count: int
    pants_present: bool
    pants_valid_toml: bool
    pants_has_backend_section: bool
    config_parse_errors: str
    skip_reason: str
