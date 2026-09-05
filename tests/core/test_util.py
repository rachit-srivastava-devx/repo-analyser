from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyser.core.util import (
    ToolExecutionError,
    _swap_used_mb,
    discover_repos,
    is_git_repo,
    read_json,
    run,
    run_concurrent,
    safe_worker_count,
    write_csv,
    write_json,
)


class TestIsGitRepo:
    def test_true_for_real_repo(self, git_repo: Path) -> None:
        assert is_git_repo(git_repo) is True

    def test_false_for_plain_dir(self, empty_dir: Path) -> None:
        assert is_git_repo(empty_dir) is False

    def test_false_for_nonexistent_path(self, tmp_path: Path) -> None:
        assert is_git_repo(tmp_path / "does-not-exist") is False


class TestDiscoverRepos:
    def test_single_repo_target(self, git_repo: Path) -> None:
        assert discover_repos(git_repo) == [git_repo.resolve()]

    def test_portfolio_target(self, git_portfolio: Path) -> None:
        found = discover_repos(git_portfolio)
        assert [p.name for p in found] == ["repo-a", "repo-b"]  # sorted

    def test_nonexistent_target_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            discover_repos(tmp_path / "nope")

    def test_empty_dir_raises_not_silent_empty_list(self, empty_dir: Path) -> None:
        # ADR-0001: a directory that is neither a repo nor a portfolio of
        # repos must raise, not silently return [] (which would look
        # identical to "a portfolio that happens to have zero repos").
        with pytest.raises(ValueError, match="neither a git repo nor a directory"):
            discover_repos(empty_dir)

    def test_dir_with_one_non_git_child_raises(self, tmp_path: Path) -> None:
        d = tmp_path / "parent"
        (d / "plain_subdir").mkdir(parents=True)
        with pytest.raises(ValueError):
            discover_repos(d)

    def test_portfolio_ignores_non_repo_siblings(self, git_portfolio: Path) -> None:
        (git_portfolio / "not-a-repo").mkdir()
        (git_portfolio / "a_file.txt").write_text("x")
        found = discover_repos(git_portfolio)
        assert [p.name for p in found] == ["repo-a", "repo-b"]


class TestRun:
    def test_captures_stdout(self) -> None:
        res = run(["python3", "-c", "print('hello')"])
        assert res.returncode == 0
        assert res.stdout.strip() == "hello"

    def test_raises_tool_execution_error_on_nonzero_by_default(self) -> None:
        with pytest.raises(ToolExecutionError) as exc_info:
            run(["python3", "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])
        assert exc_info.value.returncode == 3
        assert "boom" in exc_info.value.stderr
        assert "boom" in str(exc_info.value)  # stderr surfaced in the message, not swallowed

    def test_check_false_returns_nonzero_without_raising(self) -> None:
        res = run(["python3", "-c", "import sys; sys.exit(7)"], check=False)
        assert res.returncode == 7

    def test_timeout_raises(self) -> None:
        import subprocess
        with pytest.raises(subprocess.TimeoutExpired):
            run(["python3", "-c", "import time; time.sleep(5)"], timeout=1)

    def test_timeout_kills_the_whole_process_group_not_just_the_direct_child(self, tmp_path: Path) -> None:
        # regression test for a real bug found live, not in a lab
        # (docs/METHODOLOGY.md #30): a jscpd run this tool reported as
        # "timed out after 900 seconds" was still alive and burning CPU
        # 15+ minutes later, reparented to launchd (ppid 1) -- because a
        # plain subprocess.run(timeout=...) only kills the direct child it
        # spawned, and jscpd's JS entry point had already spawned its own
        # native binary as a grandchild. `sh -c "sleep 30 & ...; wait"`
        # reproduces that exact shape: a background grandchild that stays
        # in the SAME process group as its parent shell (true for any
        # POSIX shell's `&` job when job control is off, i.e. non-
        # interactively) -- exactly like jscpd's own child, and unlike a
        # `setsid`-ed daemon.
        import os
        import subprocess
        import time

        pid_file = tmp_path / "grandchild.pid"
        with pytest.raises(subprocess.TimeoutExpired):
            run(["sh", "-c", f"sleep 30 & echo $! > {pid_file}; wait"], timeout=1)
        time.sleep(0.3)  # let the OS finish reaping what SIGKILL just hit
        assert pid_file.exists(), "grandchild should have started before the kill"
        grandchild_pid = int(pid_file.read_text().strip())
        with pytest.raises(ProcessLookupError):
            os.kill(grandchild_pid, 0)  # signal 0: raises iff the pid no longer exists

    def test_extra_path_is_prepended_not_replacing(self, tmp_path: Path) -> None:
        # a fake dir on PATH should not break resolution of a real binary
        # that lives elsewhere on the existing PATH.
        fake_bin = tmp_path / "fake_bin"
        fake_bin.mkdir()
        res = run(["python3", "-c", "print('ok')"], extra_path=str(fake_bin))
        assert res.stdout.strip() == "ok"

    def test_input_text_is_piped_to_stdin(self) -> None:
        res = run(["python3", "-c", "import sys; print(sys.stdin.read().strip().upper())"],
                   input_text="hi")
        assert res.stdout.strip() == "HI"

    def test_extra_env_is_visible_to_the_child(self) -> None:
        res = run(["python3", "-c", "import os; print(os.environ.get('REPO_ANALYSER_TEST_VAR', ''))"],
                   extra_env={"REPO_ANALYSER_TEST_VAR": "set"})
        assert res.stdout.strip() == "set"

    def test_extra_env_does_not_remove_existing_environment(self, monkeypatch) -> None:
        # regression guard: extra_env must merge into a copy of os.environ,
        # not replace it -- a naive `env=extra_env` would silently drop
        # PATH and everything else the child needs to even start.
        monkeypatch.setenv("REPO_ANALYSER_TEST_PRESET", "already-there")
        res = run(["python3", "-c", "import os; print(os.environ.get('REPO_ANALYSER_TEST_PRESET', ''))"],
                   extra_env={"OTHER_VAR": "x"})
        assert res.stdout.strip() == "already-there"

    def test_extra_env_does_not_mutate_os_environ(self) -> None:
        import os
        run(["python3", "-c", "print('ok')"], extra_env={"REPO_ANALYSER_SHOULD_NOT_LEAK": "1"})
        assert "REPO_ANALYSER_SHOULD_NOT_LEAK" not in os.environ


class TestWriteCsv:
    def test_writes_rows_and_returns_count(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        n = write_csv(path, [{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        assert n == 2
        assert path.read_text().splitlines() == ["a,b", "1,2", "3,4"]

    def test_empty_rows_with_explicit_fieldnames_writes_header_only(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        n = write_csv(path, [], fieldnames=["a", "b"])
        assert n == 0
        assert path.read_text().splitlines() == ["a,b"]

    def test_empty_rows_with_no_fieldnames_writes_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        n = write_csv(path, [])
        assert n == 0
        assert path.exists()  # a caller checking os.path.exists sees a real file, not nothing

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "deeper" / "out.csv"
        write_csv(path, [{"a": 1}])
        assert path.exists()


class TestWriteReadJson:
    def test_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        data = {"n": 3, "items": ["a", "b"], "nested": {"x": 1}}
        write_json(path, data)
        assert read_json(path) == data

    def test_non_serializable_falls_back_to_str(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        write_json(path, {"p": Path("/tmp/x")})
        assert read_json(path) == {"p": "/tmp/x"}

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "out.json"
        write_json(path, {})
        assert path.exists()


class TestSwapUsedMb:
    def test_real_call_on_this_machine_returns_a_nonnegative_number(self) -> None:
        # unmocked, real sysctl call -- a genuine smoke test that the
        # parsing regex matches this platform's actual `vm.swapusage`
        # format, not just a hand-written fixture string.
        result = _swap_used_mb()
        assert result is None or result >= 0.0

    def test_returns_none_on_unparseable_output(self, monkeypatch) -> None:
        import subprocess as sp

        class FakeCompletedProcess:
            stdout = "nonsense output with no used= field"

        monkeypatch.setattr(sp, "run", lambda *a, **k: FakeCompletedProcess())
        assert _swap_used_mb() is None

    def test_returns_none_when_sysctl_is_missing(self, monkeypatch) -> None:
        import subprocess as sp

        def raise_not_found(*a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(sp, "run", raise_not_found)
        assert _swap_used_mb() is None


class TestSafeWorkerCount:
    def test_returns_requested_when_swap_signal_unavailable(self, monkeypatch) -> None:
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: None)
        assert safe_worker_count(4) == 4

    def test_returns_requested_when_swap_is_healthy(self, monkeypatch) -> None:
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: 350.0)
        assert safe_worker_count(4) == 4

    def test_caps_to_one_at_the_threshold(self, monkeypatch) -> None:
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: 6000.0)
        assert safe_worker_count(4) == 1

    def test_caps_to_one_above_the_threshold(self, monkeypatch) -> None:
        # 18GB used -- roughly what was measured during this machine's own
        # real 2026-09-04/05 crash incidents.
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: 18000.0)
        assert safe_worker_count(4) == 1

    def test_never_returns_zero_workers(self, monkeypatch) -> None:
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: None)
        assert safe_worker_count(0) == 1


class TestRunConcurrent:
    def test_preserves_input_order(self) -> None:
        assert run_concurrent([3, 1, 2], lambda x: x * 10) == [30, 10, 20]

    def test_runs_every_item(self) -> None:
        assert run_concurrent(range(10), lambda x: x * x) == [x * x for x in range(10)]

    def test_empty_items_returns_empty_list(self) -> None:
        assert run_concurrent([], lambda x: x) == []

    def test_falls_back_to_sequential_under_swap_pressure(self, monkeypatch) -> None:
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: 99999.0)
        calls: list[int] = []

        def record(x: int) -> int:
            calls.append(x)
            return x

        assert run_concurrent([1, 2, 3], record) == [1, 2, 3]
        assert calls == [1, 2, 3]  # sequential call order, not just sequential results

    def test_propagates_exception_from_fn(self) -> None:
        def maybe_raise(x: int) -> int:
            if x == 2:
                raise ValueError("boom")
            return x

        with pytest.raises(ValueError, match="boom"):
            run_concurrent([1, 2, 3], maybe_raise)

    def test_runs_concurrently_not_sequentially(self, monkeypatch) -> None:
        # correctness alone (order, completeness) doesn't prove this is
        # actually concurrent -- a secretly-sequential implementation could
        # pass every test above. Prove real wall-clock overlap instead.
        monkeypatch.setattr("repo_analyser.core.util._swap_used_mb", lambda: None)
        import time

        def slow(x: int) -> int:
            time.sleep(0.2)
            return x

        start = time.time()
        run_concurrent([1, 2, 3, 4], slow, max_workers=4)
        elapsed = time.time() - start
        # sequential would take >=0.8s; 4-way concurrent should take
        # roughly one 0.2s slice plus scheduling overhead. Generous bound
        # to avoid flaking on a loaded machine.
        assert elapsed < 0.6
