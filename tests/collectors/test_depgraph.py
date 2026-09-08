from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors.depgraph import (
    _aggregate,
    _analyze_go_repo,
    _analyze_js_repo,
    _analyze_python_repo,
    _py_imports,
    _py_module_name,
    _source_files,
    analyze_repo,
    run_depgraph,
)
from repo_analyser.core.util import RunResult

HAS_GO = subprocess.run(["which", "go"], capture_output=True).returncode == 0


class TestSourceFiles:
    def test_finds_ts_and_js(self, tmp_path: Path) -> None:
        (tmp_path / "a.ts").write_text("")
        (tmp_path / "b.jsx").write_text("")
        (tmp_path / "c.txt").write_text("")
        found = {Path(f).name for f in _source_files(tmp_path)}
        assert found == {"a.ts", "b.jsx"}

    def test_excludes_node_modules(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "index.js").write_text("")
        (tmp_path / "app.ts").write_text("")
        found = {Path(f).name for f in _source_files(tmp_path)}
        assert found == {"app.ts"}

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert _source_files(tmp_path) == []


class TestAggregate:
    def test_empty_modules(self) -> None:
        result = _aggregate({"modules": []}, "myrepo")
        assert result.total_modules == 0
        assert result.top_in_degree_module == ""
        assert result.circular_count == 0

    def test_filters_node_modules_sourced_modules(self) -> None:
        data = {"modules": [
            {"source": "src/app.ts", "dependencies": []},
            {"source": "node_modules/lodash/index.js", "dependencies": []},
        ]}
        result = _aggregate(data, "myrepo")
        assert result.total_modules == 1

    def test_filters_dependencies_resolved_into_node_modules(self) -> None:
        data = {"modules": [
            {"source": "src/app.ts", "dependencies": [
                {"resolved": "node_modules/lodash/index.js", "circular": False},
                {"resolved": "src/util.ts", "circular": False},
            ]},
        ]}
        result = _aggregate(data, "myrepo")
        assert result.total_dependencies == 1

    def test_circular_flag_is_counted(self) -> None:
        data = {"modules": [
            {"source": "src/a.ts", "dependencies": [{"resolved": "src/b.ts", "circular": True}]},
        ]}
        result = _aggregate(data, "myrepo")
        assert result.circular_count == 1

    def test_orphan_flag_is_counted(self) -> None:
        data = {"modules": [{"source": "src/dead.ts", "orphan": True, "dependencies": []}]}
        result = _aggregate(data, "myrepo")
        assert result.orphan_count == 1

    def test_bare_specifier_external_package_not_counted_as_internal(self) -> None:
        # a package "exports" map can resolve to a bare specifier instead of
        # a literal node_modules/... path -- must still be excluded.
        data = {"modules": [
            {"source": "src/a.ts", "dependencies": [
                {"resolved": "@medusajs/framework/workflows-sdk", "circular": False},
            ]},
        ]}
        result = _aggregate(data, "myrepo")
        assert result.top_in_degree_module == ""
        assert result.top_in_degree == 0

    def test_relative_path_dependency_counts_as_internal(self) -> None:
        data = {"modules": [
            {"source": "src/a.ts", "dependencies": [{"resolved": "./util.ts", "circular": False}]},
            {"source": "src/b.ts", "dependencies": [{"resolved": "./util.ts", "circular": False}]},
        ]}
        result = _aggregate(data, "myrepo")
        assert result.top_in_degree_module == "./util.ts"
        assert result.top_in_degree == 2


class TestAnalyzeJsRepo:
    def test_no_node_modules_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _analyze_js_repo(repo, tmp_path / "out")
        assert "no node_modules" in result.skipped_reason

    def test_npx_install_step_has_scripts_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # security regression test (docs/ARCHITECTURE.md "Security model"):
        # npx installs a tool-chosen package (dependency-cruiser) *inside*
        # whatever arbitrary target repo this tool is pointed at, so its
        # own install-time scripts must stay disabled -- npx has no
        # --ignore-scripts flag of its own, so this has to be the
        # npm_config_ignore_scripts env var specifically, not a CLI arg.
        repo = tmp_path / "repo"
        (repo / "node_modules").mkdir(parents=True)
        (repo / "a.js").write_text("module.exports = 1;\n")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["extra_env"] = kwargs.get("extra_env")
            return RunResult(cmd, 0, '{"modules": []}', "")

        monkeypatch.setattr("repo_analyser.collectors.depgraph.run", fake_run)
        _analyze_js_repo(repo, tmp_path / "out")
        assert captured["extra_env"] == {"npm_config_ignore_scripts": "true"}

    def test_dependency_cruiser_is_version_pinned(self, tmp_path: Path, monkeypatch) -> None:
        # regression test for docs/METHODOLOGY.md #33: an unpinned `npx
        # dependency-cruiser` always resolves whatever's latest (or
        # stale-cached) -- the exact "unpinned CLI silently changes
        # behavior" class of bug that hit mutmut before it was pinned.
        # This module's own directory-vs-file-list quirk a few lines above
        # was diagnosed against 18.2.0 specifically, so that's the pin.
        repo = tmp_path / "repo"
        (repo / "node_modules").mkdir(parents=True)
        (repo / "a.js").write_text("module.exports = 1;\n")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return RunResult(cmd, 0, '{"modules": []}', "")

        monkeypatch.setattr("repo_analyser.collectors.depgraph.run", fake_run)
        _analyze_js_repo(repo, tmp_path / "out")
        assert "dependency-cruiser@18.2.0" in captured["cmd"]


class TestPyModuleName:
    def test_simple_file(self, tmp_path: Path) -> None:
        f = tmp_path / "pkg" / "mod.py"
        f.parent.mkdir(parents=True)
        f.write_text("")
        assert _py_module_name(tmp_path, f) == "pkg.mod"

    def test_init_py_collapses_to_package_name(self, tmp_path: Path) -> None:
        f = tmp_path / "pkg" / "__init__.py"
        f.parent.mkdir(parents=True)
        f.write_text("")
        assert _py_module_name(tmp_path, f) == "pkg"


class TestPyImports:
    def test_plain_import(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("import os\nimport pkg.sub\n")
        assert _py_imports(f) == [["os"], ["pkg.sub"]]

    def test_from_import_returns_both_candidates_most_specific_first(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("from pkg import submodule\n")
        assert _py_imports(f) == [["pkg.submodule", "pkg"]]

    def test_from_import_multiple_names(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("from pkg import a, b\n")
        assert _py_imports(f) == [["pkg.a", "pkg"], ["pkg.b", "pkg"]]

    def test_relative_import_is_ignored(self, tmp_path: Path) -> None:
        # node.level > 0 for `from . import x` / `from .sibling import y` --
        # deliberately excluded (see the `node.level == 0` guard).
        f = tmp_path / "a.py"
        f.write_text("from . import sibling\nfrom .other import thing\n")
        assert _py_imports(f) == []

    def test_syntax_error_returns_empty_not_crash(self, tmp_path: Path) -> None:
        f = tmp_path / "broken.py"
        f.write_text("def f(:\n    pass")
        assert _py_imports(f) == []

    def test_non_utf8_bytes_do_not_crash(self, tmp_path: Path) -> None:
        f = tmp_path / "weird.py"
        f.write_bytes(b"import os\nx = '\xff\xfe'\n")
        result = _py_imports(f)
        assert result == [["os"]]


class TestAnalyzePythonRepo:
    def test_resolves_submodule_import_not_just_package(self, tmp_path: Path) -> None:
        # the historical bug this guards: `from pkg import submodule` must
        # resolve to pkg.submodule (a real internal edge), not collapse to
        # "pkg" and miss that submodule.py is the actual dependency.
        repo = tmp_path / "repo"
        (repo / "pkg").mkdir(parents=True)
        (repo / "pkg" / "__init__.py").write_text("")
        (repo / "pkg" / "submodule.py").write_text("")
        (repo / "main.py").write_text("from pkg import submodule\n")

        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.total_modules == 3
        assert result.total_dependencies == 1
        assert result.top_in_degree_module == "pkg.submodule"
        assert result.top_in_degree == 1

    def test_attribute_import_falls_back_to_package(self, tmp_path: Path) -> None:
        # `from pkg import helper_function` where helper_function is
        # defined in pkg/__init__.py itself, not pkg/helper_function.py --
        # must resolve to "pkg", the only real local module.
        repo = tmp_path / "repo"
        (repo / "pkg").mkdir(parents=True)
        (repo / "pkg" / "__init__.py").write_text("def helper_function(): pass\n")
        (repo / "main.py").write_text("from pkg import helper_function\n")

        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.top_in_degree_module == "pkg"
        assert result.top_in_degree == 1

    def test_no_py_files_reports_skipped_reason_not_empty_success(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.skipped_reason != ""
        assert result.total_modules == 0

    def test_detects_a_real_cycle(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("import b\n")
        (repo / "b.py").write_text("import a\n")
        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.circular_count == 1

    def test_excludes_venv_and_pycache(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / ".venv" / "lib").mkdir(parents=True)
        (repo / ".venv" / "lib" / "dep.py").write_text("")
        (repo / "__pycache__").mkdir()
        (repo / "__pycache__" / "app.cpython-314.pyc").write_text("")
        (repo / "app.py").write_text("")
        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.total_modules == 1

    def test_self_import_is_not_a_self_loop_edge(self, tmp_path: Path) -> None:
        # a module's own name appearing among candidates (e.g. a package
        # re-importing a name from itself) must not create a self-edge.
        repo = tmp_path / "repo"
        (repo / "pkg").mkdir(parents=True)
        (repo / "pkg" / "__init__.py").write_text("from pkg import __init__\n")
        result = _analyze_python_repo(repo, tmp_path / "out")
        assert result.total_dependencies == 0


class TestAnalyzeGoRepo:
    def test_no_go_mod_reports_skipped_reason(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _analyze_go_repo(repo, tmp_path / "out")
        assert "no go.mod" in result.skipped_reason

    def test_go_mod_without_module_directive_reports_skipped_reason(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("go 1.21\n")
        result = _analyze_go_repo(repo, tmp_path / "out")
        assert "no module directive" in result.skipped_reason

    @pytest.mark.skipif(not HAS_GO, reason="go toolchain not on PATH")
    def test_real_go_module_with_internal_dependency(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "sub").mkdir(parents=True)
        (repo / "go.mod").write_text("module example.com/repo\n\ngo 1.21\n")
        (repo / "main.go").write_text(
            'package main\n\nimport "example.com/repo/sub"\n\nfunc main() { sub.Hello() }\n'
        )
        (repo / "sub" / "sub.go").write_text('package sub\n\nfunc Hello() {}\n')

        result = _analyze_go_repo(repo, tmp_path / "out")
        assert result.skipped_reason == ""
        assert result.total_modules == 2
        assert result.total_dependencies == 1
        assert result.top_in_degree_module == "example.com/repo/sub"


class TestAnalyzeRepoLanguageDispatch:
    def test_unsupported_language_reports_skipped_reason_with_supported_list(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Main.java").write_text("")
        result = analyze_repo(repo, tmp_path / "out")
        assert "not supported" in result.skipped_reason
        assert "javascript" in result.skipped_reason  # names what IS supported


class TestRunDepgraph:
    def test_writes_one_row_per_repo(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "a"
        repo_a.mkdir()
        (repo_a / "x.py").write_text("import os\n")
        repo_b = tmp_path / "b"
        repo_b.mkdir()
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_depgraph([repo_a, repo_b], out_dir)
        rows = out_path.read_text().splitlines()
        assert len(rows) == 3  # header + 2 repos

    def test_empty_repo_list_writes_header_only_csv(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_depgraph([], out_dir)
        assert out_path.read_text().splitlines() == [
            "repo,total_modules,total_dependencies,circular_count,orphan_count,"
            "top_in_degree_module,top_in_degree,skipped_reason"
        ]
