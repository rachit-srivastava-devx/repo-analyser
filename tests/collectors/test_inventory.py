from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from repo_analyser.collectors.inventory import _gini, _tier, analyze_repo, run_inventory


class TestTier:
    @pytest.mark.parametrize("days,expected", [
        (0, "active"), (90, "active"),
        (91, "recent"), (365, "recent"),
        (366, "aging"), (1095, "aging"),
        (1096, "dormant"), (5000, "dormant"),
    ])
    def test_boundaries(self, days: int, expected: str) -> None:
        assert _tier(days) == expected


class TestGini:
    def test_empty_is_zero(self) -> None:
        assert _gini([]) == 0.0

    def test_all_zero_is_zero_not_division_error(self) -> None:
        assert _gini([0, 0, 0]) == 0.0

    def test_perfectly_equal_authorship_is_zero(self) -> None:
        assert _gini([5, 5, 5, 5]) == 0.0

    def test_single_author_is_zero(self) -> None:
        # one author, 100% share -- Gini of a single-element distribution
        # is 0 by definition (there's no inequality *between* authors).
        assert _gini([42]) == 0.0

    def test_more_unequal_scores_higher(self) -> None:
        moderate = _gini([1, 3])
        extreme = _gini([1, 100])
        assert 0 < moderate < extreme < 1

    def test_known_value_two_authors_1_and_3(self) -> None:
        # G = (2*sum((i+1)*x_i))/(n*sum(x_i)) - (n+1)/n, sorted [1,3]:
        # cum = 1*1 + 2*3 = 7; G = 14/(2*4) - 3/2 = 1.75 - 1.5 = 0.25
        assert _gini([1, 3]) == 0.25

    def test_order_of_input_does_not_matter(self) -> None:
        assert _gini([3, 1, 5]) == _gini([5, 3, 1]) == _gini([1, 3, 5])


class TestAnalyzeRepo:
    def test_basic_metrics_from_real_repo(self, git_repo: Path) -> None:
        now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        result = analyze_repo(git_repo, now=now)
        assert result.total_commits == 2
        assert result.unique_authors == 1
        assert result.merge_commits == 0
        assert result.top_author_share == 1.0
        assert result.bus_factor_gini == 0.0  # single author

    def test_tier_reflects_days_since_last_commit(self, git_repo: Path) -> None:
        recent_now = datetime.now(timezone.utc)
        result = analyze_repo(git_repo, now=recent_now)
        assert result.tier == "active"
        assert result.days_since_last_commit <= 1

    def test_far_future_now_yields_dormant(self, git_repo: Path) -> None:
        far_future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        result = analyze_repo(git_repo, now=far_future)
        assert result.tier == "dormant"

    def test_multi_author_repo_has_nonzero_gini(self, tmp_path: Path) -> None:
        import subprocess

        def git(repo: Path, *args: str, author: str) -> None:
            subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
                env={"GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": f"{author}@example.com",
                     "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": f"{author}@example.com",
                     "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
            )

        repo = tmp_path / "multi_author"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main", author="alice")
        for i in range(3):
            (repo / "f.txt").write_text(str(i))
            git(repo, "add", "f.txt", author="alice")
            git(repo, "commit", "-q", "-m", f"alice commit {i}", author="alice")
        (repo / "f.txt").write_text("bob's turn")
        git(repo, "add", "f.txt", author="bob")
        git(repo, "commit", "-q", "-m", "bob commit", author="bob")

        result = analyze_repo(repo)
        assert result.unique_authors == 2
        assert result.bus_factor_gini > 0
        assert result.top_author == "alice@example.com"
        assert result.top_author_share == 0.75


class TestRunInventory:
    def test_sorts_by_total_commits_descending(self, tmp_path: Path) -> None:
        import subprocess

        def make_repo(name: str, n_commits: int) -> Path:
            repo = tmp_path / name
            repo.mkdir()
            env = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@x.com",
                   "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@x.com",
                   "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True,
                            capture_output=True, env=env)
            for i in range(n_commits):
                (repo / "f.txt").write_text(str(i))
                subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True, capture_output=True, env=env)
                subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=repo, check=True,
                                capture_output=True, env=env)
            return repo

        small = make_repo("small", 1)
        big = make_repo("big", 3)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_inventory([small, big], out_dir)
        rows = out_path.read_text().splitlines()
        # header, then "big" (3 commits) before "small" (1 commit)
        assert "big" in rows[1]
        assert "small" in rows[2]
