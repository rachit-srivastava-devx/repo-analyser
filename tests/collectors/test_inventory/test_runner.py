from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.inventory import run_inventory


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
