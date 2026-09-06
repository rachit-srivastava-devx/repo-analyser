from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from _dead_code_helpers import write_files

from repo_analyser.collectors.dead_code.vulture_runner import (
    has_python_files,
    parse_vulture_stdout,
    run_vulture,
    vulture_available,
)

VULTURE_MISSING = shutil.which("vulture") is None


class TestHasPythonFiles:
    def test_true_when_py_file_present(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"a.py": "x = 1\n"})
        assert has_python_files(tmp_path) is True

    def test_false_for_zero_py_files(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"a.js": "const x = 1;\n"})
        assert has_python_files(tmp_path) is False

    def test_false_for_totally_empty_repo(self, tmp_path: Path) -> None:
        assert has_python_files(tmp_path) is False

    def test_ignores_excluded_dirs(self, tmp_path: Path) -> None:
        write_files(tmp_path, {"venv/lib/site.py": "x = 1\n"})
        assert has_python_files(tmp_path) is False


class TestParseVultureStdout:
    def test_parses_a_real_verified_finding_line(self, tmp_path: Path) -> None:
        # Exact line shape captured from a real, installed vulture 2.16 run
        # against a purpose-built fixture -- not a guess.
        write_files(tmp_path, {"app.py": "def helper():\n    return 1\n"})
        stdout = f"{tmp_path / 'app.py'}:1: unused function 'helper' (60% confidence)\n"
        findings = parse_vulture_stdout(stdout, tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert (f.language, f.kind, f.file, f.line, f.name) == ("python", "function", "app.py", 1, "helper")

    def test_skips_non_finding_lines(self, tmp_path: Path) -> None:
        stdout = (
            f"{tmp_path / 'broken.py'}:3: invalid syntax (<unknown>, line 3)\n"
            f"{tmp_path / 'app.py'}:5: unreachable code after 'return' (100% confidence)\n"
        )
        assert parse_vulture_stdout(stdout, tmp_path) == []

    def test_path_outside_repo_is_kept_as_is(self, tmp_path: Path) -> None:
        stdout = "/some/other/place/app.py:1: unused import 'os' (90% confidence)\n"
        findings = parse_vulture_stdout(stdout, tmp_path)
        assert findings[0].file == "/some/other/place/app.py"


class TestVultureAvailable:
    def test_reflects_real_shutil_which(self) -> None:
        assert vulture_available() == (shutil.which("vulture") is not None)


@pytest.mark.skipif(VULTURE_MISSING, reason="vulture not installed on this machine")
class TestRunVultureRealExecution:
    def test_real_unused_function_is_detected(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "app.py": "def unused_helper():\n    return 1\n\n\ndef main():\n    return 2\n\n\nmain()\n",
        })
        findings = run_vulture(tmp_path)
        assert "unused_helper" in {f.name for f in findings}
        assert "main" not in {f.name for f in findings}  # main() is called -- not unused

    def test_malformed_file_does_not_stop_scan_of_others(self, tmp_path: Path) -> None:
        write_files(tmp_path, {
            "broken.py": "def broken(:\n    pass\n",  # syntax error
            "good.py": "def unused_thing():\n    return 1\n\n\ndef main():\n    return 2\n\n\nmain()\n",
        })
        findings = run_vulture(tmp_path)  # must not raise
        assert "unused_thing" in {f.name for f in findings}

    def test_vendored_venv_dir_is_excluded_not_reported(self, tmp_path: Path) -> None:
        # Regression test: a physically-present .venv inside the repo tree
        # (a completely normal on-disk layout, not a contrived edge case --
        # this exact scenario inflated a real self-run of this collector to
        # 7144 findings before --exclude was added to run_vulture) must not
        # have its own vendored package's unused code reported as this
        # repo's dead code.
        write_files(tmp_path, {
            "app.py": "def unused_top_level():\n    return 1\n\n\ndef main():\n    return 2\n\n\nmain()\n",
            ".venv/lib/site.py": "def unused_vendored():\n    return 1\n",
        })
        names = {f.name for f in run_vulture(tmp_path)}
        assert "unused_top_level" in names
        assert "unused_vendored" not in names
