"""Tests for pr_review.flags._generated_flags."""
from __future__ import annotations

from pathlib import Path

from conftest import _git

from repo_analyser.pr_review.flags import _generated_flags


class TestGeneratedFlag:
    def test_linguist_generated_attribute_is_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "generated_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / ".gitattributes").write_text("dist/** linguist-generated=true\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add gitattributes")

        (repo / "dist").mkdir()
        (repo / "dist" / "bundle.js").write_text("// built output\n")
        (repo / "src.js").write_text("real source\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add generated and real files")
        head = _git(repo, "rev-parse", "HEAD").strip()

        flags = _generated_flags(repo, head, ["dist/bundle.js", "src.js"])
        assert flags["dist/bundle.js"] is True
        assert flags["src.js"] is False

    def test_no_gitattributes_file_defaults_to_false(self, git_repo: Path) -> None:
        head = _git(git_repo, "rev-parse", "HEAD").strip()
        flags = _generated_flags(git_repo, head, ["app.py"])
        assert flags["app.py"] is False

    def test_empty_path_list_returns_empty_dict_without_running_git(self, git_repo: Path) -> None:
        assert _generated_flags(git_repo, "HEAD", []) == {}

    def test_unset_diff_attribute_also_flags_generated(self, tmp_path: Path) -> None:
        # The `-diff` gitattributes syntax (generic "don't diff this as
        # text", commonly applied to vendored/generated files) is a
        # separate signal from `linguist-generated` -- either one alone
        # must be enough to flag is_generated.
        repo = tmp_path / "unset_diff_repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / ".gitattributes").write_text("vendored.txt -diff\n")
        (repo / "vendored.txt").write_text("third-party content\n")
        (repo / "real.txt").write_text("real content\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add gitattributes and files")
        head = _git(repo, "rev-parse", "HEAD").strip()

        flags = _generated_flags(repo, head, ["vendored.txt", "real.txt"])
        assert flags["vendored.txt"] is True
        assert flags["real.txt"] is False

    def test_check_attr_failure_fails_open_to_false(self, git_repo: Path) -> None:
        # Any check-attr failure (an old git rejecting --source, or here, a
        # source that doesn't resolve to a real tree-ish) must degrade to
        # False rather than raise -- an imperfect signal, never a crash.
        flags = _generated_flags(git_repo, "not-a-real-tree-ish", ["app.py"])
        assert flags["app.py"] is False
