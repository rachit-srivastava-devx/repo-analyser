from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from repo_analyser.collectors.inventory import analyze_repo


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
