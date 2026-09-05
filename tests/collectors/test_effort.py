from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from repo_analyser.collectors.effort import (
    TOIL_MIN_CLUSTER_SIZE,
    detect_toil_clusters,
    monthly_superclass_share,
    per_author_breakdown,
    run_effort,
)


def _commit(author="alice", superclass="delivery", date="2025-01-15T00:00:00", repo="r",
            primary_dir="src/api", leaf="feature", subject="did a thing") -> dict:
    return {"author": author, "superclass": superclass, "date": date, "repo": repo,
            "primary_dir": primary_dir, "leaf": leaf, "subject": subject}


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
