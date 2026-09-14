from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift.cross_repo_dependency_drift import (
    check_cross_repo_dependency_drift,
)
from repo_analyser.collectors.tooling_drift.dependency_versions import (
    go_mod_requires,
    package_json_deps,
)


class TestCrossRepoDependencyDrift:
    """Portfolio-wide (root-manifest) dependency-version drift -- the same
    dependency name pinned to different versions across DIFFERENT repos'
    root manifests, as opposed to dependency_version_check.py's within-
    one-repo sibling-manifest comparison. See
    cross_repo_dependency_drift.py's own docstring for the row-shape
    decision each test below exercises."""

    def test_shared_dependency_pinned_differently_across_repos_is_drift(self, tmp_path: Path) -> None:
        a, b, c = (_mkrepo(tmp_path, n) for n in ("svc-a", "svc-b", "svc-c"))
        (a / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (b / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (c / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))

        rows, summary = check_cross_repo_dependency_drift([a, b, c], "package.json", "package.json", package_json_deps)

        assert summary.ecosystem == "package.json"
        assert summary.repos_compared == 3
        assert summary.dependencies_compared == 1
        assert summary.dependencies_drifted == 1
        assert summary.skipped_reason == ""
        assert len(rows) == 1
        row = rows[0]
        assert row.dependency_name == "lodash"
        assert row.ecosystem == "package.json"
        assert row.versions_found == "^3.0.0;^4.17.0"
        assert row.repo_count == 3
        # both sides of the divergence are visible, grouped by version.
        assert "^3.0.0:svc-c" in row.repos_by_version
        assert "^4.17.0:svc-a,svc-b" in row.repos_by_version

    def test_full_agreement_across_repos_produces_no_rows(self, tmp_path: Path) -> None:
        a, b = (_mkrepo(tmp_path, n) for n in ("svc-a", "svc-b"))
        for repo in (a, b):
            (repo / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))

        rows, summary = check_cross_repo_dependency_drift([a, b], "package.json", "package.json", package_json_deps)

        assert rows == []
        assert summary.dependencies_compared == 1
        assert summary.dependencies_drifted == 0
        assert summary.skipped_reason == ""

    def test_dependency_declared_in_only_one_repo_is_not_compared(self, tmp_path: Path) -> None:
        """Two repos with entirely disjoint dependency names -- nothing
        shared, so nothing is "compared" at all (matches
        dependency_drift.py's own >=2-occurrences threshold, not relaxed
        here)."""
        a, b = (_mkrepo(tmp_path, n) for n in ("svc-a", "svc-b"))
        (a / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (b / "package.json").write_text(json.dumps({"dependencies": {"requests-shim": "1.0.0"}}))

        rows, summary = check_cross_repo_dependency_drift([a, b], "package.json", "package.json", package_json_deps)

        assert rows == []
        assert summary.dependencies_compared == 0
        assert summary.dependencies_drifted == 0
        assert summary.skipped_reason == ""

    def test_single_repo_portfolio_is_skipped_entirely(self, tmp_path: Path) -> None:
        a = _mkrepo(tmp_path, "svc-a")
        (a / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))

        rows, summary = check_cross_repo_dependency_drift([a], "package.json", "package.json", package_json_deps)

        assert rows == []
        assert summary.repos_compared == 0
        assert summary.skipped_reason

    def test_empty_portfolio_is_skipped_entirely(self) -> None:
        rows, summary = check_cross_repo_dependency_drift([], "package.json", "package.json", package_json_deps)

        assert rows == []
        assert summary.skipped_reason

    def test_no_repo_has_the_manifest_at_root_is_skipped(self, tmp_path: Path) -> None:
        """Two real repos, neither with a root package.json at all --
        distinct from "manifests exist but nothing shared", since here
        there is nothing to even attempt parsing."""
        a, b = (_mkrepo(tmp_path, n) for n in ("svc-a", "svc-b"))

        rows, summary = check_cross_repo_dependency_drift([a, b], "package.json", "package.json", package_json_deps)

        assert rows == []
        assert summary.repos_compared == 0
        assert "package.json" in summary.skipped_reason

    def test_duplicate_repo_path_does_not_double_count(self, tmp_path: Path) -> None:
        """The same physical repo passed twice (e.g. a symlink alias)
        must collapse to one vote -- otherwise it could manufacture a
        drift finding (or inflate repo_count) purely from being counted
        twice, exactly the failure `dedupe_by_real_path` exists to
        prevent for the lint dimension too."""
        a = _mkrepo(tmp_path, "svc-a")
        (a / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        alias = tmp_path / "svc-a-alias"
        alias.symlink_to(a)
        b = _mkrepo(tmp_path, "svc-b")
        (b / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))

        rows, summary = check_cross_repo_dependency_drift(
            [a, alias, b], "package.json", "package.json", package_json_deps
        )

        assert summary.repos_compared == 2  # alias collapsed into `a`, not a third distinct repo
        assert len(rows) == 1
        assert rows[0].repo_count == 2

    def test_go_mod_ecosystem_is_compared_independently(self, tmp_path: Path) -> None:
        a, b = (_mkrepo(tmp_path, n) for n in ("svc-a", "svc-b"))
        (a / "go.mod").write_text("module example.com/svc-a\n\ngo 1.21\n\nrequire github.com/pkg/errors v0.9.1\n")
        (b / "go.mod").write_text("module example.com/svc-b\n\ngo 1.21\n\nrequire github.com/pkg/errors v0.8.0\n")

        rows, summary = check_cross_repo_dependency_drift([a, b], "go.mod", "go.mod", go_mod_requires)

        assert summary.ecosystem == "go.mod"
        assert len(rows) == 1
        assert rows[0].dependency_name == "github.com/pkg/errors"
        assert rows[0].ecosystem == "go.mod"
        assert rows[0].versions_found == "v0.8.0;v0.9.1"
