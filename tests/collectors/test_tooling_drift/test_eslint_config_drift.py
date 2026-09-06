from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestEslintConfigDrift:
    """A monorepo where one package has an eslint config and a sibling
    package of the same shape doesn't."""

    def test_one_package_has_eslintrc_sibling_does_not(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text("{}")
        (repo / "pkg-a" / ".eslintrc.json").write_text(json.dumps({"extends": "airbnb"}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text("{}")

        rows = analyze_repo(repo)
        eslint_rows = [r for r in rows if r.config_kind == "eslint"]
        assert len(eslint_rows) == 1
        row = eslint_rows[0]
        assert row.packages_compared == 2
        assert row.packages_with_drift == 1
        assert "missing" in row.drift_detail
        assert ".eslintrc.json" in row.drift_detail
        assert row.skip_reason == ""

    def test_identical_eslintrc_content_is_not_drift(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        for name in ("pkg-a", "pkg-b"):
            (repo / name).mkdir()
            (repo / name / "package.json").write_text("{}")
            (repo / name / ".eslintrc.json").write_text(json.dumps({"extends": "airbnb"}))

        rows = analyze_repo(repo)
        assert not any(r.config_kind == "eslint" for r in rows)

    def test_same_filename_different_content_is_drift(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text("{}")
        (repo / "pkg-a" / ".eslintrc.json").write_text(json.dumps({"extends": "airbnb"}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text("{}")
        (repo / "pkg-b" / ".eslintrc.json").write_text(json.dumps({"extends": "standard"}))

        rows = analyze_repo(repo)
        eslint_rows = [r for r in rows if r.config_kind == "eslint"]
        assert len(eslint_rows) == 1
        assert eslint_rows[0].packages_with_drift == 1
