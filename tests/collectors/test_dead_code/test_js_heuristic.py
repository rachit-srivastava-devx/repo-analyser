from __future__ import annotations

from pathlib import Path

from _dead_code_helpers import write_files

from repo_analyser.collectors.dead_code.js_heuristic import extract_exports, js_ts_files, scan_repo


class TestExtractExports:
    def test_named_const_export(self) -> None:
        assert extract_exports("export const foo = 1;\n") == {"foo": 1}

    def test_named_function_export(self) -> None:
        assert extract_exports("export function bar() {}\n") == {"bar": 1}

    def test_default_named_export(self) -> None:
        assert extract_exports("export default function baz() {}\n") == {"baz": 1}

    def test_default_bare_identifier_export(self) -> None:
        content = "function qux() {}\nexport default qux;\n"
        assert extract_exports(content) == {"qux": 2}

    def test_anonymous_default_export_has_no_name_to_track(self) -> None:
        assert extract_exports("export default () => {};\n") == {}

    def test_brace_named_export_list_with_alias(self) -> None:
        content = "const a = 1, b = 2;\nexport { a, b as bAlias };\n"
        assert extract_exports(content) == {"a": 2, "bAlias": 2}

    def test_reexport_only_does_not_double_count(self) -> None:
        assert extract_exports("export { x } from './y';\n") == {"x": 1}


class TestJsTsFiles:
    def test_finds_only_tracked_extensions(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"a.js": "", "b.ts": "", "c.py": "", "d.txt": ""})
        assert {p.name for p in js_ts_files(tmp_path)} == {"a.js", "b.ts"}

    def test_excludes_node_modules(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"node_modules/pkg/index.js": "export const x = 1;\n"})
        assert js_ts_files(tmp_path) == []

    def test_empty_repo_returns_empty_list(self, tmp_path: Path) -> None:
        assert js_ts_files(tmp_path) == []


class TestScanRepo:
    def test_unreferenced_export_is_flagged_referenced_one_is_not(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "used.js": "export const usedThing = 1;\n",
            "unused.js": "export const unusedThing = 2;\n",
            "consumer.js": "import { usedThing } from './used.js';\nconsole.log(usedThing);\n",
        })
        findings = scan_repo(tmp_path, js_ts_files(tmp_path))
        names = {f.name for f in findings}
        assert "unusedThing" in names
        assert "usedThing" not in names

    def test_reexport_only_file_is_not_double_counted(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "barrel.js": "export { x } from './y';\n",
            "other.js": "const z = 1;\n",  # never mentions 'x' at all
        })
        findings = scan_repo(tmp_path, js_ts_files(tmp_path))
        barrel_findings = [f for f in findings if f.file == "barrel.js"]
        assert len(barrel_findings) == 1
        assert barrel_findings[0].name == "x"

    def test_missing_file_in_list_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        # A path that vanished between being listed and being read (e.g. a
        # TOCTOU race, or a caller passing a stale list) raises
        # FileNotFoundError (an OSError) on read_text -- must not be fatal
        # to the rest of the scan.
        write_files(tmp_path, {"a.js": "export const x = 1;\n"})
        files = js_ts_files(tmp_path) + [tmp_path / "ghost.js"]  # never written to disk
        findings = scan_repo(tmp_path, files)  # must not raise
        assert any(f.name == "x" for f in findings)
