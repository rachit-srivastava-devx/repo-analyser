"""Tests for pr_review.diff.get_changed_files's is_lockfile/is_excluded
flags (assembled in pr_review.assemble)."""
from __future__ import annotations

from pathlib import Path

from _pr_review_helpers import _ctx
from conftest import _git

from repo_analyser.pr_review.diff import get_changed_files


class TestLockfileAndExcludedFlags:
    def test_known_lockfile_name_is_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "lockfile_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "commit", "--allow-empty", "-q", "-m", "empty root")
        merge_base = _git(repo, "rev-parse", "HEAD").strip()

        (repo / "package-lock.json").write_text("{}\n")
        (repo / "app.py").write_text("print(1)\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add lockfile and app code")
        head = _git(repo, "rev-parse", "HEAD").strip()

        changed = {cf.path: cf for cf in get_changed_files(repo, _ctx(merge_base, head))}
        assert changed["package-lock.json"].is_lockfile is True
        assert changed["app.py"].is_lockfile is False

    def test_excluded_dir_part_is_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "excluded_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "commit", "--allow-empty", "-q", "-m", "empty root")
        merge_base = _git(repo, "rev-parse", "HEAD").strip()

        (repo / "node_modules").mkdir()
        (repo / "node_modules" / "dep.js").write_text("module.exports = {};\n")
        (repo / "src").mkdir()
        (repo / "src" / "app.js").write_text("console.log(1);\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add vendored and real code")
        head = _git(repo, "rev-parse", "HEAD").strip()

        changed = {cf.path: cf for cf in get_changed_files(repo, _ctx(merge_base, head))}
        assert changed["node_modules/dep.js"].is_excluded is True
        assert changed["src/app.js"].is_excluded is False
