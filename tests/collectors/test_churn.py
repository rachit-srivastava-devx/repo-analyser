from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors import churn
from repo_analyser.collectors.churn import _code_maat_jar, run_churn

HAS_JAVA = subprocess.run(["which", "java"], capture_output=True).returncode == 0
HAS_JAR = _code_maat_jar().exists()
pytestmark = pytest.mark.skipif(not (HAS_JAVA and HAS_JAR), reason="java + tools/code-maat.jar required")


class TestCodeMaatJarPath:
    def test_resolves_to_a_real_existing_jar_by_default(self) -> None:
        # exercises repo_root() actually finding pyproject.toml correctly
        # from this package's real installed depth -- the whole reason
        # ADR-0002's fix exists.
        assert _code_maat_jar().name == "code-maat.jar"
        assert _code_maat_jar().exists()

    def test_env_var_overrides_default_location(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("REPO_ANALYSER_TOOLS_DIR", str(tmp_path))
        assert _code_maat_jar() == tmp_path / "code-maat.jar"


class TestRunChurnRealExecution:
    def test_real_repo_produces_revisions_and_coupling(self, git_repo: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        rev_path, coup_path = run_churn([git_repo], out_dir, tmp_path / "maat_logs")
        rev_rows = rev_path.read_text().splitlines()
        assert len(rev_rows) >= 2  # header + at least one file
        assert "app.py" in rev_path.read_text()
        # not asserting on coupling content: code-maat needs >=2 files
        # co-changing to report any coupling at all, and the fixture only
        # touches one file -- an empty (header-only or no-file) coupling
        # output here is a real, correct answer, not a test gap.
        assert coup_path.exists()

    def test_a_repo_that_fails_does_not_abort_the_whole_run(self, git_repo: Path, tmp_path: Path, monkeypatch) -> None:
        # regression test for a real bug found while writing this suite:
        # this except-block's `from .util import write_json` was a broken
        # relative import (util.py lives in core/, not collectors/) left
        # over from the src-layout restructuring -- it would only surface
        # once a repo actually hit this error path, which nothing exercised
        # until this test. See ADR-0002.
        def boom(repo, tmp_dir):
            raise RuntimeError("simulated code-maat failure")

        monkeypatch.setattr(churn, "analyze_repo", boom)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        rev_path, _coup_path = run_churn([git_repo], out_dir, tmp_path / "maat_logs")
        assert rev_path.exists()  # the run completed and wrote (empty) output
        errors = json.loads((out_dir / "churn_errors.json").read_text())
        assert errors[git_repo.name] == "simulated code-maat failure"
