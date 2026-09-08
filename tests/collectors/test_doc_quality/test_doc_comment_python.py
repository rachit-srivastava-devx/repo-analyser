from __future__ import annotations

from pathlib import Path

import pytest
from _doc_quality_helpers import HAS_INTERROGATE

from repo_analyser.collectors.doc_quality.doc_comment_python import _python_doc_coverage


class TestPythonDocCoverage:
    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_measures_real_mixed_coverage(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            '"""Module a docstring."""\n\n\n'
            'def documented():\n    """This is documented."""\n    return 1\n\n\n'
            'def undocumented():\n    return 2\n\n\n'
            'class Foo:\n    """Docstring."""\n\n'
            '    def method_ok(self):\n        """ok."""\n        return 1\n\n'
            '    def method_missing(self):\n        return 2\n'
        )
        (tmp_path / "b.py").write_text("def bare():\n    return 3\n")
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert tool == "interrogate"
        assert skip_reason == ""
        assert pct == 50.0  # empirically verified: 8 items total, 4 covered

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_fully_documented_repo_reports_100(self, tmp_path: Path) -> None:
        (tmp_path / "full.py").write_text(
            '"""Module docstring."""\n\n\ndef documented():\n    """Doc."""\n    return 1\n'
        )
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert pct == 100.0
        assert tool == "interrogate"

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_no_python_files_reports_skip_reason_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello\n")
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert tool == ""
        assert pct == 0.0
        assert "no Python files found by interrogate" == skip_reason

    def test_empty_dir_reports_skip_reason_not_crash(self, tmp_path: Path) -> None:
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert tool == ""
        assert skip_reason != ""

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_syntax_error_file_reports_skip_reason_not_fake_measurement(self, tmp_path: Path) -> None:
        # Confirmed live: interrogate crashes with an uncaught traceback
        # (not a clean per-file skip) the instant any .py file anywhere in
        # the tree has a genuine syntax error -- even when other files are
        # fine. Must surface as a named skip_reason, not a fabricated 0.0
        # read as "0% documented", and not an unhandled exception bubbling
        # out of this module.
        (tmp_path / "good.py").write_text('"""Doc."""\n\n\ndef f():\n    """Doc."""\n    return 1\n')
        (tmp_path / "bad.py").write_text("def broken(:\n    pass\n")
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert tool == ""
        assert pct == 0.0
        assert "interrogate produced unparseable output" in skip_reason

    @pytest.mark.skipif(not HAS_INTERROGATE, reason="interrogate not on PATH")
    def test_vendor_and_build_dirs_are_excluded_from_coverage(self, tmp_path: Path) -> None:
        (tmp_path / "real.py").write_text('"""Doc."""\n\n\ndef documented():\n    """Doc."""\n    return 1\n')
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "generated.py").write_text("def undocumented_generated():\n    return 1\n")
        vendor_dir = tmp_path / "vendor"
        vendor_dir.mkdir()
        (vendor_dir / "thirdparty.py").write_text("def undocumented_thirdparty():\n    return 1\n")
        pct, tool, skip_reason = _python_doc_coverage(tmp_path)
        assert pct == 100.0  # would be 33.3 if build/ and vendor/ were not excluded
        assert tool == "interrogate"
