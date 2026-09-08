from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors import complexity
from repo_analyser.collectors.complexity import (
    _norm,
    aggregate_by_file,
    analyze_repo_functions,
    run_complexity,
)

HAS_LIZARD = subprocess.run(["which", "lizard"], capture_output=True).returncode == 0
pytestmark = pytest.mark.skipif(not HAS_LIZARD, reason="lizard not on PATH")


class TestNorm:
    def test_strips_leading_dot_slash(self) -> None:
        assert _norm("./src/app.py") == "src/app.py"

    def test_leaves_other_paths_unchanged(self) -> None:
        assert _norm("src/app.py") == "src/app.py"


class TestAggregateByFile:
    def test_sums_ccn_and_counts_functions_per_file(self) -> None:
        rows = [
            {"repo": "r", "file": "a.py", "ccn": 3, "nloc": 10},
            {"repo": "r", "file": "a.py", "ccn": 5, "nloc": 20},
            {"repo": "r", "file": "b.py", "ccn": 1, "nloc": 5},
        ]
        agg = {(a["repo"], a["file"]): a for a in aggregate_by_file(rows)}
        assert agg[("r", "a.py")]["total_ccn"] == 8
        assert agg[("r", "a.py")]["max_ccn"] == 5
        assert agg[("r", "a.py")]["function_count"] == 2
        assert agg[("r", "b.py")]["total_ccn"] == 1

    def test_empty_input(self) -> None:
        assert aggregate_by_file([]) == []


class TestAnalyzeRepoFunctionsExcludes:
    """Regression tests: EXCLUDES used to be its own 6-entry list here,
    independently drifted from core.lang.EXCLUDE_DIR_PARTS, missing
    target/vendor/venv/.venv/__pycache__/.turbo -- a Rust repo's `target/`
    build directory would have gone straight into a real lizard scan."""

    def test_rust_target_dir_is_excluded(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "src.rs").write_text("fn main() {}\n")
        target_dir = repo / "target" / "debug"
        target_dir.mkdir(parents=True)
        (target_dir / "generated.rs").write_text("fn g() {\n" + "if true {}\n" * 20 + "}\n")
        rows = analyze_repo_functions(repo)
        assert all("target" not in r["file"] for r in rows)

    def test_venv_dir_is_excluded(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("def f():\n    return 1\n")
        venv_dir = repo / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "dep.py").write_text("def g():\n    return 2\n")
        rows = analyze_repo_functions(repo)
        assert all(".venv" not in r["file"] for r in rows)


class TestRunComplexityRealExecution:
    def test_real_repo_produces_hotspots_joined_with_churn(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text(
            "def f(x):\n    if x:\n        if x > 1:\n            return 1\n"
            "    return 0\n"
        )
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        churn_csv = out_dir / "churn_revisions.csv"
        churn_csv.write_text("repo,entity,n-revs\nrepo,app.py,7\n")

        hotspot_path = run_complexity([repo], out_dir, churn_csv=churn_csv)
        rows = hotspot_path.read_text().splitlines()
        assert len(rows) == 2  # header + app.py
        assert "app.py" in rows[1]
        # hotspot_score = total_ccn * n_revs; n_revs=7 from the churn csv join
        assert ",7," in rows[1] or rows[1].endswith("7") or "7" in rows[1].split(",")[-2:]

    def test_no_churn_csv_defaults_n_revs_to_zero_not_a_crash(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("def f():\n    return 1\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        hotspot_path = run_complexity([repo], out_dir, churn_csv=None)
        rows = hotspot_path.read_text().splitlines()
        assert rows[1].split(",")[-2] == "0"  # n_revs column

    def test_a_repo_that_fails_does_not_abort_the_whole_run(self, tmp_path: Path, monkeypatch) -> None:
        # same bug class as churn.py's regression test: the `if errors:`
        # branch's import was broken by the src-layout move and nothing
        # exercised it until this test.
        def boom(repo):
            raise RuntimeError("simulated lizard failure")

        monkeypatch.setattr(complexity, "analyze_repo_functions", boom)
        repo = tmp_path / "repo"
        repo.mkdir()
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        hotspot_path = run_complexity([repo], out_dir)
        assert hotspot_path.read_text().splitlines() == [
            "repo,file,total_ccn,max_ccn,function_count,total_nloc,n_revs,hotspot_score"
        ]
        func_path = out_dir / "complexity_functions.csv"
        assert func_path.read_text().splitlines() == [
            "repo,file,function,nloc,ccn,tokens,params,length,start_line,end_line"
        ]
        errors = json.loads((out_dir / "complexity_errors.json").read_text())
        assert errors[repo.name] == "simulated lizard failure"
