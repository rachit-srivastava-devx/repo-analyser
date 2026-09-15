from __future__ import annotations

import json
import subprocess
from pathlib import Path

from repo_analyser.collectors.escape import _blame_map, run_escape


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_NAME": "Dev", "GIT_AUTHOR_EMAIL": "dev@example.com",
             "GIT_COMMITTER_NAME": "Dev", "GIT_COMMITTER_EMAIL": "dev@example.com",
             "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"},
    )


class TestBlameMap:
    def test_blames_the_introducing_commit(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "f.py").write_text("x = 1\n")
        _git(repo, "add", "f.py")
        _git(repo, "commit", "-q", "-m", "feat: add f")
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

        blame = _blame_map(repo, sha, "f.py")
        assert blame == {1: sha}

    def test_nonexistent_file_returns_empty_not_crash(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "f.py").write_text("x = 1\n")
        _git(repo, "add", "f.py")
        _git(repo, "commit", "-q", "-m", "feat: add f")
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
        assert _blame_map(repo, sha, "does_not_exist.py") == {}


class TestRunEscapeEndToEnd:
    """A real, minimal SZZ case: commit 1 introduces a line, commit 2 (a
    `fix:` commit) changes that exact line -- `git blame` on commit 1's
    version must attribute the deleted line back to commit 1."""

    def test_attributes_the_fix_to_its_real_introducing_commit(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "calc.py").write_text("def total(a, b):\n    return a - b\n")  # introduces the bug
        _git(repo, "add", "calc.py")
        _git(repo, "commit", "-q", "-m", "feat: add total()")
        introducing_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

        (repo / "calc.py").write_text("def total(a, b):\n    return a + b\n")  # the actual fix
        _git(repo, "add", "calc.py")
        _git(repo, "commit", "-q", "-m", "fix: total() subtracted instead of adding")
        fix_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_escape([repo], out_dir)

        rows = out_path.read_text().splitlines()
        assert len(rows) == 2  # header + 1 real escape
        assert introducing_sha[:10] in rows[1]
        assert fix_sha[:10] in rows[1]

        summary = json.loads((out_dir / "escape_summary.json").read_text())
        assert summary["total_escapes_attributed"] == 1
        assert summary["per_repo_fix_commit_stats"]["repo"]["total_fix_commits"] == 1
        assert summary["per_repo_fix_commit_stats"]["repo"]["escapes_found"] == 1

    def test_a_fix_with_only_additions_is_a_pure_addition_fix_not_an_escape(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "calc.py").write_text("def total(a, b):\n    return a + b\n")
        _git(repo, "add", "calc.py")
        _git(repo, "commit", "-q", "-m", "feat: add total()")

        (repo / "calc.py").write_text(
            "def total(a, b):\n    return a + b\n\n\n"
            "def missing_check(x):\n    if x is None:\n        raise ValueError\n"
        )
        _git(repo, "add", "calc.py")
        _git(repo, "commit", "-q", "-m", "fix: add missing None check")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_escape([repo], out_dir)
        summary = json.loads((out_dir / "escape_summary.json").read_text())
        assert summary["total_escapes_attributed"] == 0
        assert summary["per_repo_fix_commit_stats"]["repo"]["pure_addition_or_unattributed_fixes"] == 1

    def test_no_fix_commits_produces_valid_empty_output(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "f.py").write_text("x = 1\n")
        _git(repo, "add", "f.py")
        _git(repo, "commit", "-q", "-m", "feat: initial")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_escape([repo], out_dir)
        assert out_path.read_text().splitlines() == [
            "repo,fix_sha,fix_date,file,introducing_sha,introducing_date,latency_days"
        ]
        summary = json.loads((out_dir / "escape_summary.json").read_text())
        assert summary["total_escapes_attributed"] == 0
        assert summary["latency_days_median"] is None  # no crash on an empty percentile
