from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestDependencyVersionDrift:
    """The same dependency name pinned to different version strings
    across sibling package.json manifests."""

    def test_same_dependency_different_versions_is_drift(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))

        rows = analyze_repo(repo)
        drift_rows = [r for r in rows if r.config_kind == "dependency_version"]
        assert len(drift_rows) == 1
        row = drift_rows[0]
        assert row.packages_compared == 1
        assert row.packages_with_drift == 1
        assert "lodash@^4.17.0" in row.drift_detail
        assert "lodash@^3.0.0" in row.drift_detail
        assert row.skip_reason == ""

    def test_same_dependency_same_version_is_not_drift(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))

        rows = analyze_repo(repo)
        # both package.json manifests were compared (>=2 found) and eslint
        # config state matches (neither has one) -- a clean, legitimate
        # "nothing wrong" result produces zero rows, not a skip row.
        assert rows == []

    def test_dependency_named_in_only_one_manifest_is_not_compared(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(
            json.dumps({"dependencies": {"lodash": "^4.17.0", "left-pad": "^1.0.0"}})
        )
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))

        rows = analyze_repo(repo)
        # left-pad only appears in one manifest -- nothing to compare it
        # against, so it must not appear in drift_detail at all.
        assert not any("left-pad" in r.drift_detail for r in rows)

    def test_go_mod_same_module_different_versions_across_siblings(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "svc-a").mkdir()
        (repo / "svc-a" / "go.mod").write_text(
            "module example.com/svc-a\n\ngo 1.21\n\nrequire github.com/pkg/errors v0.9.1\n"
        )
        (repo / "svc-b").mkdir()
        (repo / "svc-b" / "go.mod").write_text(
            "module example.com/svc-b\n\ngo 1.21\n\nrequire (\n\tgithub.com/pkg/errors v0.8.0 // indirect\n)\n"
        )

        rows = analyze_repo(repo)
        drift_rows = [r for r in rows if r.config_kind == "dependency_version"]
        assert len(drift_rows) == 1
        assert "github.com/pkg/errors@v0.9.1" in drift_rows[0].drift_detail
        assert "github.com/pkg/errors@v0.8.0" in drift_rows[0].drift_detail
