from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.monorepo_tooling.analyze import analyze_repo

from ._monorepo_tooling_helpers import write


def test_empty_repo_no_config_files_at_all(tmp_path: Path) -> None:
    result = analyze_repo(tmp_path)

    assert result.orchestrator_count == 0
    assert result.orchestrators_detected == ""
    assert result.nx_present is False
    assert result.turbo_present is False
    assert result.bazel_present is False
    assert result.buck_present is False
    assert result.pants_present is False
    assert result.skip_reason != ""


def test_unicode_content_in_config_files(tmp_path: Path) -> None:
    write(
        tmp_path,
        "nx.json",
        '{"targetDefaults": {"build": {"comment": "日本語 😀"}}}',
    )
    write(tmp_path, "pants.toml", '[GLOBAL]\nname = "café-monorepo"\n')

    result = analyze_repo(tmp_path)

    assert result.nx_present is True
    assert result.nx_valid_json is True
    assert result.nx_has_configured_graph is True
    assert result.pants_present is True
    assert result.pants_valid_toml is True


def test_huge_build_file_count_bounded_scan_excludes_vendor_dirs(tmp_path: Path) -> None:
    write(tmp_path, "WORKSPACE", "workspace(name = \"big\")\n")
    for i in range(50):
        write(tmp_path, f"pkg{i}/BUILD.bazel", f'cc_library(name = "pkg{i}")\n')
    # A vendored/node_modules-style directory full of BUILD-named files must
    # not inflate the count -- these are excluded the same way every other
    # filesystem-walking collector excludes them (core.lang.EXCLUDE_DIR_PARTS).
    for i in range(20):
        write(tmp_path, f"node_modules/dep{i}/BUILD", "not ours\n")

    result = analyze_repo(tmp_path)

    assert result.bazel_build_file_count == 50


def test_multiple_orchestrators_present_at_once_migration(tmp_path: Path) -> None:
    write(tmp_path, "nx.json", '{"targetDefaults": {}}')
    write(tmp_path, "turbo.json", '{"tasks": {"build": {}}}')
    write(tmp_path, "WORKSPACE", "workspace(name = \"m\")\n")
    write(tmp_path, ".buckconfig", "[repositories]\n")
    write(tmp_path, "pants.toml", "[GLOBAL]\n")

    result = analyze_repo(tmp_path)

    assert set(result.orchestrators_detected.split(";")) == {"nx", "turbo", "bazel", "buck2", "pants"}
    assert result.orchestrator_count == 5
    assert result.skip_reason == ""


def test_nested_monorepo_within_monorepo_not_found_at_non_root(tmp_path: Path) -> None:
    """Documented, deliberate limitation: orchestrator config files are
    checked at the repo root only. A workspace config nested one level
    down is not discovered by this collector."""
    write(tmp_path, "nested-workspace/nx.json", '{"targetDefaults": {}}')

    result = analyze_repo(tmp_path)

    assert result.nx_present is False
    assert result.orchestrator_count == 0
