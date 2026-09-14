from __future__ import annotations

from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift.cross_repo_drift import check_cross_repo_lint_drift
from repo_analyser.collectors.tooling_drift.lint_configs import eslint_display


class TestCrossRepoCanonicalConfig:
    """Majority/canonical detection for the portfolio-wide (cross-repo)
    lint-config dimension -- see cross_repo_drift.py's own docstring for
    the design decisions each test below exercises."""

    def test_majority_fingerprint_is_canonical_minority_drifts(self, tmp_path: Path) -> None:
        a, b, c = (_mkrepo(tmp_path, n) for n in ("a", "b", "c"))
        for repo in (a, b):
            (repo / "package.json").write_text("{}")
            (repo / ".eslintrc.json").write_text('{"extends": "airbnb"}')
        (c / "package.json").write_text("{}")
        (c / ".eslintrc.json").write_text('{"extends": "standard"}')

        rows, summary = check_cross_repo_lint_drift([a, b, c], "cross_repo_eslint", "package.json", eslint_display)

        assert summary.repos_compared == 3
        assert summary.repos_drifted == 1
        assert summary.skipped_reason == ""
        assert [r.repo for r in rows] == ["c"]
        assert rows[0].packages_with_drift == 1
        assert "a:" in rows[0].drift_detail
        assert "b:" in rows[0].drift_detail
        assert "c:" in rows[0].drift_detail

    def test_missing_config_can_itself_be_canonical(self, tmp_path: Path) -> None:
        """Two repos have a root package.json but no eslint config at all
        ("missing"); one repo declares a real config. "missing" is the
        majority and therefore canonical -- the repo with real config is
        the drifted outlier, not the other way around."""
        a, b, c = (_mkrepo(tmp_path, n) for n in ("a", "b", "c"))
        (a / "package.json").write_text("{}")
        (b / "package.json").write_text("{}")
        (c / "package.json").write_text("{}")
        (c / ".eslintrc.json").write_text('{"extends": "airbnb"}')

        rows, summary = check_cross_repo_lint_drift([a, b, c], "cross_repo_eslint", "package.json", eslint_display)

        assert summary.canonical_fingerprint == "missing"
        assert [r.repo for r in rows] == ["c"]

    def test_repo_without_root_manifest_is_excluded_not_counted_as_missing(self, tmp_path: Path) -> None:
        """A repo with no root package.json at all contributes nothing to
        the eslint vote -- distinct from a repo that HAS a root
        package.json but declares no eslint config ("missing")."""
        a, b, no_manifest = (_mkrepo(tmp_path, n) for n in ("a", "b", "no-manifest"))
        for repo in (a, b):
            (repo / "package.json").write_text("{}")
            (repo / ".eslintrc.json").write_text('{"extends": "airbnb"}')

        rows, summary = check_cross_repo_lint_drift(
            [a, b, no_manifest], "cross_repo_eslint", "package.json", eslint_display
        )

        assert summary.repos_compared == 2  # not 3 -- no_manifest is absent, not a "missing" vote
        assert rows == []

    def test_tie_breaks_lexicographically_smallest_fingerprint(self, tmp_path: Path) -> None:
        """Two repos fingerprint "missing", two repos share a real eslint
        config hash -- an exact 2-2 tie. Pins the tie-break against the
        real fingerprint strings rather than assuming which one wins."""
        a, b, c, d = (_mkrepo(tmp_path, n) for n in ("a", "b", "c", "d"))
        for repo in (a, b):
            (repo / "package.json").write_text("{}")  # fingerprint == "missing"
        for repo in (c, d):
            (repo / "package.json").write_text("{}")
            (repo / ".eslintrc.json").write_text('{"extends": "airbnb"}')

        rows, summary = check_cross_repo_lint_drift([a, b, c, d], "cross_repo_eslint", "package.json", eslint_display)

        fingerprint_c = eslint_display(c / "package.json")
        assert summary.canonical_fingerprint == min("missing", fingerprint_c)
        assert summary.repos_drifted == 2  # the two repos NOT holding the tie-break winner

    def test_single_repo_portfolio_is_skipped_entirely(self, tmp_path: Path) -> None:
        a = _mkrepo(tmp_path, "a")
        (a / "package.json").write_text("{}")

        rows, summary = check_cross_repo_lint_drift([a], "cross_repo_eslint", "package.json", eslint_display)

        assert rows == []
        assert summary.canonical_fingerprint is None
        assert summary.skipped_reason

    def test_empty_portfolio_is_skipped_entirely(self) -> None:
        rows, summary = check_cross_repo_lint_drift([], "cross_repo_eslint", "package.json", eslint_display)

        assert rows == []
        assert summary.canonical_fingerprint is None
        assert summary.skipped_reason

    def test_duplicate_repo_path_does_not_double_count(self, tmp_path: Path) -> None:
        """The same physical repo passed twice (e.g. a symlink alias) must
        collapse to one vote, not silently out-vote a genuinely distinct
        repo."""
        a = _mkrepo(tmp_path, "a")
        (a / "package.json").write_text("{}")
        (a / ".eslintrc.json").write_text('{"extends": "airbnb"}')
        b = _mkrepo(tmp_path, "b")
        (b / "package.json").write_text("{}")
        alias = tmp_path / "a-alias"
        alias.symlink_to(a)

        rows, summary = check_cross_repo_lint_drift(
            [a, alias, b], "cross_repo_eslint", "package.json", eslint_display
        )

        assert summary.repos_compared == 2  # alias collapsed into `a`, not a third distinct vote
