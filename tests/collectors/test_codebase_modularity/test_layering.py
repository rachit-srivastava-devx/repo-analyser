from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codebase_modularity.layering import find_layering_findings

from ._codebase_modularity_helpers import init_repo, write


def test_no_config_detected_reports_empty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "README.md", "hello\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == ""
    assert result.layering_config_path == ""


def test_dependency_cruiser_dotfile_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, ".dependency-cruiser.js", "module.exports = {};\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "dependency-cruiser"
    assert ".dependency-cruiser.js" in result.layering_config_path


def test_dependency_cruiser_package_json_key_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "package.json", '{"name": "x", "depcruise": {"forbidden": []}}')
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "dependency-cruiser"
    assert "package.json" in result.layering_config_path


def test_malformed_package_json_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "package.json", "{not valid json")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == ""


def test_import_linter_dotfile_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, ".importlinter", "[importlinter]\nroot_package = foo\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "import-linter"
    assert ".importlinter" in result.layering_config_path


def test_import_linter_pyproject_table_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "pyproject.toml", "[tool.importlinter]\nroot_package = \"foo\"\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "import-linter"
    assert "pyproject.toml" in result.layering_config_path


def test_import_linter_setup_cfg_section_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "setup.cfg", "[importlinter]\nroot_package = foo\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "import-linter"
    assert "setup.cfg" in result.layering_config_path


def test_malformed_setup_cfg_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "setup.cfg", "this is not = valid [ini")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == ""


def test_pyproject_without_importlinter_table_not_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "pyproject.toml", "[tool.ruff]\nline-length = 120\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == ""


def test_go_arch_lint_detected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, ".go-arch-lint.yml", "version: 3\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "go-arch-lint"
    assert ".go-arch-lint.yml" in result.layering_config_path


def test_multiple_tools_detected_at_once_reported_independently(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, ".dependency-cruiser.json", "{}")
    write(repo, ".importlinter", "[importlinter]\n")
    result = find_layering_findings(repo)
    assert "dependency-cruiser" in result.layering_tool_detected
    assert "import-linter" in result.layering_tool_detected
    assert result.layering_tool_detected.count(";") == 1


def test_no_language_gate_js_repo_with_import_linter_leftover_still_detected(tmp_path: Path) -> None:
    """Presence detection shouldn't assume based on dominant language --
    a JS-dominant repo with a leftover .importlinter from a migration
    must still be reported."""
    repo = init_repo(tmp_path / "r")
    write(repo, "index.js", "console.log('hi');\n")
    write(repo, ".importlinter", "[importlinter]\n")
    result = find_layering_findings(repo)
    assert result.layering_tool_detected == "import-linter"
