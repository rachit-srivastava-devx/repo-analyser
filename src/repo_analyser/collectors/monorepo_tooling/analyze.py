"""Per-repo orchestration: combines nx/turbo/bazel/buck2/pants signal
detection into one MonorepoToolingResult. See package docstring for the
full contract, including the root-only-vs-recursive scoping decision:
orchestrator config-file presence is checked at the repo root only
(matching each tool's own workspace-root convention, and ci_gates.py's own
root-only .github/workflows precedent); BUILD/BUCK/project.json files are
counted via a single bounded recursive walk (fs_scan.py) since those
legitimately live throughout the tree."""
from __future__ import annotations

from pathlib import Path

from .bazel_signals import analyze_bazel, analyze_buck
from .fs_scan import count_files_by_name
from .models import MonorepoToolingResult
from .nx_signals import analyze_nx
from .pants_signals import analyze_pants
from .patterns import SCANNED_FILENAMES
from .turbo_signals import analyze_turbo


def analyze_repo(repo: Path) -> MonorepoToolingResult:
    file_counts = count_files_by_name(repo, SCANNED_FILENAMES)

    nx_present, nx_valid, nx_configured, nx_projects, nx_err = analyze_nx(repo, file_counts)
    turbo_present, turbo_valid, turbo_schema, turbo_tasks, turbo_err = analyze_turbo(repo)
    bazel_present, bazel_markers, bazel_build_count = analyze_bazel(repo, file_counts)
    buck_present, buck_build_count = analyze_buck(repo, file_counts)
    pants_present, pants_valid, pants_backend, pants_err = analyze_pants(repo)

    present_flags = (nx_present, turbo_present, bazel_present, buck_present, pants_present)
    names = ("nx", "turbo", "bazel", "buck2", "pants")
    orchestrators = [name for name, present in zip(names, present_flags, strict=True) if present]

    parse_errors = [e for e in (nx_err, turbo_err, pants_err) if e]

    skip_reason = "" if orchestrators else (
        "no monorepo build/task orchestrator config detected "
        "(nx.json, turbo.json, WORKSPACE/WORKSPACE.bazel/MODULE.bazel, "
        ".buckconfig, or pants.toml)"
    )

    return MonorepoToolingResult(
        repo=repo.name,
        orchestrators_detected=";".join(orchestrators),
        orchestrator_count=len(orchestrators),
        nx_present=nx_present,
        nx_valid_json=nx_valid,
        nx_has_configured_graph=nx_configured,
        nx_project_json_count=nx_projects,
        turbo_present=turbo_present,
        turbo_valid_json=turbo_valid,
        turbo_schema=turbo_schema,
        turbo_task_count=turbo_tasks,
        bazel_present=bazel_present,
        bazel_workspace_markers=bazel_markers,
        bazel_build_file_count=bazel_build_count,
        buck_present=buck_present,
        buck_build_file_count=buck_build_count,
        pants_present=pants_present,
        pants_valid_toml=pants_valid,
        pants_has_backend_section=pants_backend,
        config_parse_errors=";".join(parse_errors),
        skip_reason=skip_reason,
    )
