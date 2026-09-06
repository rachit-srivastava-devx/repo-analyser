from __future__ import annotations

from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestRuffConfigDrift:
    def test_one_pyproject_has_tool_ruff_table_sibling_does_not(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "pyproject.toml").write_text(
            "[project]\nname = \"a\"\n\n[tool.ruff]\nline-length = 100\n"
        )
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "pyproject.toml").write_text("[project]\nname = \"b\"\n")

        rows = analyze_repo(repo)
        ruff_rows = [r for r in rows if r.config_kind == "ruff"]
        assert len(ruff_rows) == 1
        assert ruff_rows[0].packages_compared == 2
        assert ruff_rows[0].packages_with_drift == 1
        assert "missing" in ruff_rows[0].drift_detail
        assert "tool.ruff" in ruff_rows[0].drift_detail
