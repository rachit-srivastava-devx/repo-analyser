from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.monorepo_tooling.analyze import analyze_repo

from ._monorepo_tooling_helpers import write


def test_bazel_workspace_and_build_files_detected(tmp_path: Path) -> None:
    write(tmp_path, "WORKSPACE", 'workspace(name = "example")\n')
    write(tmp_path, "BUILD.bazel", 'cc_library(name = "foo")\n')
    write(tmp_path, "services/api/BUILD", 'go_binary(name = "api")\n')
    write(tmp_path, "services/worker/BUILD.bazel", 'go_binary(name = "worker")\n')

    result = analyze_repo(tmp_path)

    assert result.bazel_present is True
    assert "WORKSPACE" in result.bazel_workspace_markers.split(";")
    assert result.bazel_build_file_count == 3
    assert "bazel" in result.orchestrators_detected.split(";")


def test_bazel_bzlmod_only_no_workspace_file(tmp_path: Path) -> None:
    write(tmp_path, "MODULE.bazel", 'module(name = "example")\n')

    result = analyze_repo(tmp_path)

    assert result.bazel_present is True
    assert result.bazel_workspace_markers == "MODULE.bazel"
    assert result.bazel_build_file_count == 0


def test_buck2_config_and_build_files_detected(tmp_path: Path) -> None:
    write(tmp_path, ".buckconfig", "[repositories]\nroot = .\n")
    write(tmp_path, "apps/cli/BUCK", 'cxx_binary(name = "cli")\n')

    result = analyze_repo(tmp_path)

    assert result.buck_present is True
    assert result.buck_build_file_count == 1
    assert "buck2" in result.orchestrators_detected.split(";")


def test_build_file_unrelated_content_still_counted_by_filename_only(tmp_path: Path) -> None:
    """Documented limitation: a BUILD file with content unrelated to Bazel
    (e.g. a hand-written build-instructions doc) is indistinguishable from
    a real Bazel BUILD file, since this collector never parses content."""
    write(tmp_path, "BUILD", "Run `make all` then `make install`.\nNo Starlark here.\n")

    result = analyze_repo(tmp_path)

    assert result.bazel_present is True
    assert result.bazel_build_file_count == 1


def test_no_bazel_or_buck_signals_in_plain_repo(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "hello\n")

    result = analyze_repo(tmp_path)

    assert result.bazel_present is False
    assert result.buck_present is False
    assert result.bazel_build_file_count == 0
    assert result.buck_build_file_count == 0
