from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from repo_analyser.collectors.effort import (
    TOIL_MIN_CLUSTER_SIZE,
    _gini,
    _top_decile_share,
    detect_toil_clusters,
    monthly_superclass_share,
    per_author_breakdown,
    run_effort,
)
from repo_analyser.collectors.inventory.tiering import _gini as inventory_gini


def _commit(author="alice", superclass="delivery", date="2025-01-15T00:00:00", repo="r",
            primary_dir="src/api", leaf="feature", subject="did a thing") -> dict:
    return {"author": author, "superclass": superclass, "date": date, "repo": repo,
            "primary_dir": primary_dir, "leaf": leaf, "subject": subject}


ONTOLOGY_FIELDNAMES = ["repo", "sha", "author", "date", "is_merge", "subject", "leaf",
                       "superclass", "matched_rule", "primary_dir", "file_count"]


def _ontology_row(repo: str, author: str, sha: str, superclass: str = "delivery",
                   leaf: str = "feature", date: str = "2025-01-01T00:00:00") -> dict:
    """One row as it would actually appear in ontology_commits.csv. is_merge
    is always "False" -- ontology.py excludes merge commits before writing
    a row at all (see effort.py's module docstring), so there is no
    real-world row with is_merge=True to construct here."""
    return {"repo": repo, "sha": sha, "author": author, "date": date, "is_merge": "False",
            "subject": "did a thing", "leaf": leaf, "superclass": superclass,
            "matched_rule": "message:x", "primary_dir": "src", "file_count": "1"}


def _write_ontology_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ONTOLOGY_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


class TestPerAuthorBreakdown:
    def test_single_author_single_category_is_100pct(self) -> None:
        commits = [_commit(superclass="delivery") for _ in range(5)]
        result = per_author_breakdown(commits)
        assert len(result) == 1
        assert result[0].total_commits == 5
        assert result[0].delivery_pct == 100.0
        assert result[0].correction_pct == 0.0

    def test_mixed_categories_percentages_sum_to_100(self) -> None:
        commits = ([_commit(superclass="delivery")] * 3 + [_commit(superclass="correction")] * 1)
        result = per_author_breakdown(commits)
        row = result[0]
        total_pct = (row.delivery_pct + row.correction_pct + row.code_health_pct +
                     row.ops_config_pct + row.data_schema_pct + row.housekeeping_pct + row.other_pct)
        assert total_pct == 100.0
        assert row.delivery_pct == 75.0
        assert row.correction_pct == 25.0

    def test_sorted_by_total_commits_descending(self) -> None:
        commits = [_commit(author="prolific")] * 10 + [_commit(author="occasional")] * 2
        result = per_author_breakdown(commits)
        assert [r.author for r in result] == ["prolific", "occasional"]

    def test_empty_commits_returns_empty_list(self) -> None:
        assert per_author_breakdown([]) == []


class TestMonthlySuperclassShare:
    def test_groups_by_month_prefix(self) -> None:
        commits = [_commit(date="2025-01-15T00:00:00"), _commit(date="2025-01-20T00:00:00"),
                   _commit(date="2025-02-01T00:00:00")]
        result = monthly_superclass_share(commits)
        assert [r["month"] for r in result] == ["2025-01", "2025-02"]
        assert result[0]["total_commits"] == 2
        assert result[1]["total_commits"] == 1

    def test_shares_are_fractions_not_percentages(self) -> None:
        commits = [_commit(superclass="delivery")] * 3 + [_commit(superclass="correction")] * 1
        result = monthly_superclass_share(commits)
        assert result[0]["delivery"] == 0.75
        assert result[0]["correction"] == 0.25

    def test_empty_commits_returns_empty_list(self) -> None:
        assert monthly_superclass_share([]) == []


class TestDetectToilClusters:
    def test_below_threshold_is_not_a_cluster(self) -> None:
        commits = [_commit(superclass="ops_config") for _ in range(TOIL_MIN_CLUSTER_SIZE - 1)]
        assert detect_toil_clusters(commits) == []

    def test_at_threshold_is_a_cluster(self) -> None:
        commits = [_commit(superclass="ops_config", author=f"a{i}") for i in range(TOIL_MIN_CLUSTER_SIZE)]
        clusters = detect_toil_clusters(commits)
        assert len(clusters) == 1
        assert clusters[0]["commit_count"] == TOIL_MIN_CLUSTER_SIZE
        assert clusters[0]["distinct_authors"] == TOIL_MIN_CLUSTER_SIZE

    def test_delivery_commits_never_form_a_toil_cluster(self) -> None:
        commits = [_commit(superclass="delivery") for _ in range(50)]
        assert detect_toil_clusters(commits) == []

    def test_commits_with_no_primary_dir_are_excluded(self) -> None:
        commits = [_commit(superclass="ops_config", primary_dir="") for _ in range(50)]
        assert detect_toil_clusters(commits) == []

    def test_different_dirs_form_separate_clusters(self) -> None:
        commits = ([_commit(superclass="ops_config", primary_dir="src/a") for _ in range(TOIL_MIN_CLUSTER_SIZE)] +
                   [_commit(superclass="ops_config", primary_dir="src/b") for _ in range(TOIL_MIN_CLUSTER_SIZE)])
        clusters = detect_toil_clusters(commits)
        assert len(clusters) == 2

    def test_sorted_by_commit_count_descending(self) -> None:
        small = [_commit(superclass="ops_config", primary_dir="src/small") for _ in range(TOIL_MIN_CLUSTER_SIZE)]
        big = [_commit(superclass="ops_config", primary_dir="src/big") for _ in range(TOIL_MIN_CLUSTER_SIZE + 10)]
        clusters = detect_toil_clusters(small + big)
        assert clusters[0]["primary_dir"] == "src/big"

    def test_dominant_leaf_is_the_most_common_one_in_the_cluster(self) -> None:
        commits = ([_commit(superclass="ops_config", leaf="ci_build") for _ in range(10)] +
                   [_commit(superclass="ops_config", leaf="chore") for _ in range(5)])
        clusters = detect_toil_clusters(commits)
        assert clusters[0]["dominant_leaf"] == "ci_build"


class TestGini:
    def test_empty_is_zero(self) -> None:
        assert _gini([]) == 0.0

    def test_all_zero_is_zero(self) -> None:
        assert _gini([0, 0, 0]) == 0.0

    def test_single_author_is_zero(self) -> None:
        assert _gini([42]) == 0.0

    def test_perfectly_even_authorship_is_zero(self) -> None:
        assert _gini([20, 20, 20]) == 0.0

    def test_skewed_distribution_matches_mean_absolute_difference_formula(self) -> None:
        counts = [1, 2, 3, 4]
        # Independent cross-check: the well-known mean-absolute-difference
        # form of the Gini coefficient, computed here without reusing any of
        # _gini's own rank-based arithmetic, so this isn't just restating
        # the implementation under a different name.
        n = len(counts)
        alt = round(sum(abs(a - b) for a in counts for b in counts) / (2 * n * sum(counts)), 4)
        assert _gini(counts) == 0.25
        assert _gini(counts) == alt


class TestTopDecileShare:
    def test_empty_is_zero(self) -> None:
        assert _top_decile_share([]) == (0, 0.0)

    def test_two_authors_top_decile_collapses_to_top_one(self) -> None:
        # ceil(10% of 2) rounds up to 1 -- "top decile" is never zero authors.
        assert _top_decile_share([20, 20]) == (1, 0.5)

    def test_eleven_authors_top_decile_is_two(self) -> None:
        # ceil(10% of 11) == 2, not 1 -- the count returned alongside the
        # share is what makes that rounding rule checkable by hand.
        counts = [100] + [1] * 10
        assert _top_decile_share(counts) == (2, 0.9182)


class TestRunEffort:
    def test_raises_on_empty_ontology_csv(self, tmp_path: Path) -> None:
        ontology_csv = tmp_path / "ontology_commits.csv"
        ontology_csv.write_text("repo,sha,author,date,is_merge,subject,leaf,superclass,matched_rule,primary_dir,file_count\n")
        with pytest.raises(ValueError, match="no rows"):
            run_effort(ontology_csv, tmp_path)

    def test_writes_all_three_outputs_from_a_real_csv(self, tmp_path: Path) -> None:
        ontology_csv = tmp_path / "ontology_commits.csv"
        fieldnames = ["repo", "sha", "author", "date", "is_merge", "subject", "leaf",
                      "superclass", "matched_rule", "primary_dir", "file_count"]
        with open(ontology_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for i in range(20):
                w.writerow({"repo": "r", "sha": f"sha{i}", "author": "alice",
                            "date": "2025-01-01T00:00:00", "is_merge": "False",
                            "subject": "chore: bump", "leaf": "dependency_bump",
                            "superclass": "ops_config", "matched_rule": "file:dependency_bump",
                            "primary_dir": "root", "file_count": "1"})

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        author_path = run_effort(ontology_csv, out_dir)
        assert author_path.exists()
        assert (out_dir / "effort_monthly_share.csv").exists()
        assert (out_dir / "effort_toil_clusters.csv").exists()

        summary = json.loads((out_dir / "effort_summary.json").read_text())
        assert summary["total_commits"] == 20
        assert summary["toil_clusters_found"] == 1
        assert summary["toil_commits_in_clusters"] == 20


class TestRunEffortContributionGini:
    """Portfolio-wide contribution concentration end to end: build a real
    (multi-repo, where relevant) ontology_commits.csv, run `run_effort`, and
    read `effort_summary.json` back -- the same "trace back to a rerunnable
    command" bar the rest of this codebase holds itself to. Expected Gini
    values are computed by hand in a comment and cross-checked against the
    mean-absolute-difference formula in `TestGini`, not just re-derived from
    `_gini` itself."""

    def test_perfectly_even_authorship_across_a_multi_repo_portfolio_is_zero_gini(
        self, tmp_path: Path
    ) -> None:
        # alice and bob each commit 20 times to r1 and 20 times to r2 --
        # 40 commits each, portfolio-wide -- so the two-repo split is
        # invisible to the per-author total; counts=[40, 40] -> gini=0.
        rows = []
        for repo in ("r1", "r2"):
            for author in ("alice", "bob"):
                rows += [_ontology_row(repo, author, sha=f"{repo}-{author}-{i}") for i in range(20)]
        ontology_csv = tmp_path / "ontology_commits.csv"
        _write_ontology_csv(ontology_csv, rows)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_effort(ontology_csv, out_dir)

        summary = json.loads((out_dir / "effort_summary.json").read_text())
        assert summary["total_authors"] == 2
        assert summary["contribution_gini_portfolio_wide"] == 0.0

    def test_one_dominant_author_across_the_whole_portfolio_pushes_gini_high(self, tmp_path: Path) -> None:
        # alice commits to *both* repos, 50 times each (100 total); 10 other
        # authors commit once each to exactly one of the two repos. Alice's
        # dominance (100 of 110 commits, ~91%) is only visible once counts
        # are summed across repos -- per-repo she's "only" 50 of 55 (~91%
        # too, coincidentally similar here, but each minor author would look
        # like a much bigger share of *their own* repo alone than they are
        # of the portfolio). counts=[100, 1x10] -> gini=0.8182 (see TestGini
        # and TestTopDecileShare for this exact distribution's numbers).
        rows = []
        rows += [_ontology_row("r1", "alice", sha=f"r1-alice-{i}") for i in range(50)]
        rows += [_ontology_row("r2", "alice", sha=f"r2-alice-{i}") for i in range(50)]
        rows += [_ontology_row("r1", f"minor-r1-{i}", sha=f"r1-minor-{i}") for i in range(5)]
        rows += [_ontology_row("r2", f"minor-r2-{i}", sha=f"r2-minor-{i}") for i in range(5)]
        ontology_csv = tmp_path / "ontology_commits.csv"
        _write_ontology_csv(ontology_csv, rows)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_effort(ontology_csv, out_dir)

        summary = json.loads((out_dir / "effort_summary.json").read_text())
        assert summary["total_authors"] == 11
        assert summary["contribution_gini_portfolio_wide"] == 0.8182
        assert summary["contribution_top10pct_author_count"] == 2
        assert summary["contribution_top10pct_commit_share"] == 0.9182

    def test_author_committing_to_only_one_of_several_repos_is_still_summed_correctly(
        self, tmp_path: Path
    ) -> None:
        # alice: 6 commits in r1 + 6 in r2 = 12 total. bob: r1 only (4).
        # carol: r2 only (4). Nothing here should require the caller to pass
        # a repo list separately -- summing across repos is just what
        # grouping the whole run's commits by author already does.
        rows = []
        rows += [_ontology_row("r1", "alice", sha=f"r1-alice-{i}") for i in range(6)]
        rows += [_ontology_row("r2", "alice", sha=f"r2-alice-{i}") for i in range(6)]
        rows += [_ontology_row("r1", "bob", sha=f"r1-bob-{i}") for i in range(4)]
        rows += [_ontology_row("r2", "carol", sha=f"r2-carol-{i}") for i in range(4)]
        ontology_csv = tmp_path / "ontology_commits.csv"
        _write_ontology_csv(ontology_csv, rows)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        author_path = run_effort(ontology_csv, out_dir)

        with open(author_path) as f:
            by_author = {r["author"]: int(r["total_commits"]) for r in csv.DictReader(f)}
        assert by_author == {"alice": 12, "bob": 4, "carol": 4}

        summary = json.loads((out_dir / "effort_summary.json").read_text())
        assert summary["contribution_gini_portfolio_wide"] == 0.2667

    def test_single_repo_run_matches_inventorys_per_repo_bus_factor_gini(self, tmp_path: Path) -> None:
        """A single-repo run (len(repos) == 1, i.e. discover_repos returned
        exactly one path) still computes a valid portfolio-wide Gini, and --
        because it's the exact same formula `inventory.py` applies for
        bus_factor_gini -- it is numerically identical to that one repo's
        own bus-factor Gini, for the same author/commit-count distribution.
        This equivalence holds only when the repo has no merge commits:
        `ontology.py` (this module's input) excludes merge commits from the
        population by construction (see effort.py's module docstring and
        `_ontology_row`'s comment above), while `inventory.py`'s
        bus_factor_gini comes from raw `git log --all` output that still
        includes them. This fixture is merge-free, so the two are exactly
        equal -- not just close."""
        counts = {"a": 1, "b": 2, "c": 3, "d": 4}
        rows = []
        for author, n in counts.items():
            rows += [_ontology_row("solo-repo", author, sha=f"{author}-{i}") for i in range(n)]
        ontology_csv = tmp_path / "ontology_commits.csv"
        _write_ontology_csv(ontology_csv, rows)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_effort(ontology_csv, out_dir)

        summary = json.loads((out_dir / "effort_summary.json").read_text())
        assert summary["contribution_gini_portfolio_wide"] == 0.25
        assert inventory_gini(list(counts.values())) == summary["contribution_gini_portfolio_wide"]
