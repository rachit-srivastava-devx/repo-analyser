from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from _dead_code_helpers import write_files

from repo_analyser.collectors.dead_code.analyze import analyze_repo
from repo_analyser.collectors.dead_code.models import Finding

VULTURE_MISSING = shutil.which("vulture") is None


class TestNoApplicableFiles:
    def test_zero_py_files_python_fields_are_none_cleanly(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"a.js": "export const x = 1;\n"})
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python is None
        # not-applicable (no .py files) is not the same as "tool missing".
        assert "vulture" not in result.tool_unavailable

    def test_zero_js_files_js_field_is_none_cleanly(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"a.py": "x = 1\n"})
        result = analyze_repo(tmp_path)
        assert result.unreferenced_export_count_js is None

    def test_totally_empty_repo_both_fields_none_and_no_crash(self, tmp_path: Path) -> None:
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python is None
        assert result.unreferenced_export_count_js is None
        assert result.findings == []
        assert result.tool_unavailable == []


class TestVultureUnavailableDegradesGracefully:
    def test_missing_vulture_reports_unavailable_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_files(tmp_path, {"a.py": "x = 1\n"})
        monkeypatch.setattr(
            "repo_analyser.collectors.dead_code.analyze.vulture_available", lambda: False
        )
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python is None
        assert "vulture" in result.tool_unavailable


class TestVultureSubprocessFailureIsolated:
    def test_run_vulture_exception_does_not_crash_whole_repo_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_files(tmp_path, {"a.py": "x = 1\n"})
        monkeypatch.setattr(
            "repo_analyser.collectors.dead_code.analyze.vulture_available", lambda: True
        )

        def _boom(repo: Path) -> list[Finding]:
            raise TimeoutError("simulated vulture timeout")

        monkeypatch.setattr("repo_analyser.collectors.dead_code.analyze.run_vulture", _boom)
        result = analyze_repo(tmp_path)  # must not raise
        assert result.dead_code_items_python is None
        assert "vulture" in result.tool_unavailable
        assert result.repo == tmp_path.name  # rest of the result is still well-formed


class TestJsOnlyReexportEdgeCase:
    def test_reexport_only_file_no_crash_no_doublecount(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "barrel.js": "export { x } from './y';\n",
            "other.js": "const z = 1;\n",
        })
        result = analyze_repo(tmp_path)
        assert result.unreferenced_export_count_js == 1


class TestFindingsCap:
    def test_findings_list_is_capped_but_count_field_is_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_files(tmp_path, {"a.py": "x = 1\n"})
        monkeypatch.setattr(
            "repo_analyser.collectors.dead_code.analyze.vulture_available", lambda: True
        )
        fake_findings = [
            Finding(language="python", kind="function", file="a.py", line=i, name=f"f{i}")
            for i in range(60)
        ]
        monkeypatch.setattr(
            "repo_analyser.collectors.dead_code.analyze.run_vulture", lambda repo: fake_findings
        )
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python == 60  # true count, uncapped
        assert len(result.findings) == 50  # detail list, capped


@pytest.mark.skipif(VULTURE_MISSING, reason="vulture not installed on this machine")
class TestRealVultureIntegration:
    def test_clean_python_repo_reports_zero_not_none(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"app.py": "def add(a, b):\n    return a + b\n\n\nprint(add(1, 2))\n"})
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python == 0  # checked, found nothing -- not None

    def test_real_unused_function_is_counted(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "app.py": "def unused():\n    return 1\n\n\ndef main():\n    return 2\n\n\nmain()\n",
        })
        result = analyze_repo(tmp_path)
        assert result.dead_code_items_python == 1
