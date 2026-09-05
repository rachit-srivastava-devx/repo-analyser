from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_analyser.collectors.duplication import DEFAULT_JSCPD_TIMEOUT_S, _jscpd_timeout, _split_repo, run_duplication

HAS_JSCPD = subprocess.run(["which", "jscpd"], capture_output=True).returncode == 0


class TestSplitRepo:
    def test_splits_repo_and_relative_path(self) -> None:
        assert _split_repo("posx-comet-admin/scripts/foo.js") == ("posx-comet-admin", "scripts/foo.js")

    def test_no_slash_returns_whole_string_as_repo(self) -> None:
        assert _split_repo("bare-name") == ("bare-name", "")

    def test_only_splits_on_first_slash(self) -> None:
        assert _split_repo("repo/a/b/c.js") == ("repo", "a/b/c.js")


class TestJscpdTimeout:
    def test_defaults_when_env_var_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("REPO_ANALYSER_JSCPD_TIMEOUT", raising=False)
        assert _jscpd_timeout() == DEFAULT_JSCPD_TIMEOUT_S

    def test_env_var_overrides_default(self, monkeypatch) -> None:
        # regression test for docs/METHODOLOGY.md #30: the 900s default
        # was proven insufficient twice against a real large portfolio --
        # this is the escape hatch, not another hardcoded guess.
        monkeypatch.setenv("REPO_ANALYSER_JSCPD_TIMEOUT", "1800")
        assert _jscpd_timeout() == 1800


@pytest.mark.skipif(not HAS_JSCPD, reason="jscpd not on PATH")
class TestRunDuplicationRealExecution:
    def test_identical_block_across_two_repos_is_flagged_cross_repo(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        # a real duplicated block: >=10 lines, >=70 tokens (the module's
        # own defaults) so jscpd actually reports it rather than skipping
        # a too-small match.
        block = "\n".join(f"    value_{i} = {i} * 2 + {i}" for i in range(20))
        content = f"def compute():\n{block}\n    return value_0\n"
        for repo_name in ("repo-a", "repo-b"):
            f = portfolio / repo_name / "src" / "shared.py"
            f.parent.mkdir(parents=True)
            f.write_text(content)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        repos = [portfolio / "repo-a", portfolio / "repo-b"]
        run_duplication(portfolio, out_dir, repos=repos)

        summary = json.loads((out_dir / "duplication_summary.json").read_text())
        assert summary["cross_repo_clone_pairs"] >= 1
        assert summary["cross_repo_duplicated_lines"] > 0
        assert summary["identical_relative_path_clusters"] == 1

    def test_gitignored_directories_are_not_scanned(self, tmp_path: Path) -> None:
        # regression test for docs/METHODOLOGY.md #36: --no-gitignore used
        # to force jscpd to scan gitignored content (build output, vendored
        # deps, runtime logs) regardless of a repo's own .gitignore -- real
        # evidence pointed at this as the actual cause of repeated
        # portfolio-scale timeouts. A block duplicated between a real
        # source file and a gitignored one must NOT be reported: jscpd's
        # own default (which this module now uses) respects .gitignore.
        portfolio = tmp_path / "portfolio"
        block = "\n".join(f"    value_{i} = {i} * 2 + {i}" for i in range(20))
        content = f"def compute():\n{block}\n    return value_0\n"
        repo = portfolio / "repo-a"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "shared.py").write_text(content)
        (repo / ".gitignore").write_text("ignored_build/\n")
        (repo / "ignored_build").mkdir()
        (repo / "ignored_build" / "shared_copy.py").write_text(content)
        # jscpd's gitignore-respecting behavior needs a real .git present --
        # a bare .gitignore file with no repository is not meaningful to it,
        # exactly as it wouldn't be to git itself.
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_duplication(portfolio, out_dir, repos=[repo])

        summary = json.loads((out_dir / "duplication_summary.json").read_text())
        assert summary["within_repo_clone_pairs"] == 0

    def test_no_duplication_produces_valid_empty_output(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        (portfolio / "repo-a" / "src").mkdir(parents=True)
        (portfolio / "repo-a" / "src" / "a.py").write_text("def a():\n    return 1\n")
        (portfolio / "repo-b" / "src").mkdir(parents=True)
        (portfolio / "repo-b" / "src" / "b.py").write_text("def b():\n    return 2\n")

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        repos = [portfolio / "repo-a", portfolio / "repo-b"]
        out_path = run_duplication(portfolio, out_dir, repos=repos)
        assert out_path.exists()
        summary = json.loads((out_dir / "duplication_summary.json").read_text())
        assert summary["cross_repo_clone_pairs"] == 0

    def test_language_detection_selects_python_format_not_default_js(self, tmp_path: Path) -> None:
        # regression-style check: a pure-Python portfolio must not silently
        # fall back to the JS/TS-only default format list and find nothing
        # simply because it never looked at .py files.
        portfolio = tmp_path / "portfolio"
        # dense enough to clear jscpd's default min_tokens=70 over 20 lines
        # (a sparser "v{i} = {i}" block was tried first and fell short of
        # the token floor -- verified by raising density, not assumed).
        block = "\n".join(f"    value_{i} = {i} * 2 + {i}" for i in range(20))
        for repo_name in ("repo-a", "repo-b"):
            f = portfolio / repo_name / "mod.py"
            f.parent.mkdir(parents=True)
            f.write_text(f"def f():\n{block}\n    return value_0\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        repos = [portfolio / "repo-a", portfolio / "repo-b"]
        run_duplication(portfolio, out_dir, repos=repos)
        summary = json.loads((out_dir / "duplication_summary.json").read_text())
        assert summary["cross_repo_clone_pairs"] >= 1
