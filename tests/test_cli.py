from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo_analyser.cli import cmd_analyze


def _args(target: Path, out: Path, modules: str | None = None,
          skip_slow: bool = False, retry_failed: bool = False) -> argparse.Namespace:
    return argparse.Namespace(target=str(target), out=str(out), modules=modules,
                               skip_slow=skip_slow, retry_failed=retry_failed)


class TestRetryFailed:
    def test_no_prior_run_log_is_a_clear_error(self, git_repo: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        exit_code = cmd_analyze(_args(git_repo, out, retry_failed=True))
        assert exit_code == 2

    def test_retries_only_the_failed_module(self, git_repo: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        # inventory succeeds; pdf fails deterministically and fast (no
        # deep_reports run first) -- a real, controllable failure with no
        # need for a slow/subprocess-heavy module.
        cmd_analyze(_args(git_repo, out, modules="inventory,pdf"))
        first_log = json.loads((out / "run_log.json").read_text())["modules_run"]
        assert {r["module"]: r["status"] for r in first_log} == {"inventory": "ok", "pdf": "error"}

        exit_code = cmd_analyze(_args(git_repo, out, retry_failed=True))
        assert exit_code == 1  # pdf fails again for the same real reason -- that's expected
        second_log = json.loads((out / "run_log.json").read_text())["modules_run"]
        statuses = {r["module"]: r["status"] for r in second_log}
        assert statuses == {"inventory": "ok", "pdf": "error"}

    def test_untouched_modules_keep_their_prior_result_not_rerun(self, git_repo: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        cmd_analyze(_args(git_repo, out, modules="inventory,pdf"))
        first_log = {r["module"]: r for r in json.loads((out / "run_log.json").read_text())["modules_run"]}

        cmd_analyze(_args(git_repo, out, retry_failed=True))
        second_log = {r["module"]: r for r in json.loads((out / "run_log.json").read_text())["modules_run"]}

        # inventory's own recorded result is untouched -- retry only acts
        # on what actually failed, not a full re-run of everything.
        assert second_log["inventory"] == first_log["inventory"]

    def test_nothing_to_retry_when_everything_already_passed(self, git_repo: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        cmd_analyze(_args(git_repo, out, modules="inventory,ontology"))
        exit_code = cmd_analyze(_args(git_repo, out, retry_failed=True))
        assert exit_code == 0
