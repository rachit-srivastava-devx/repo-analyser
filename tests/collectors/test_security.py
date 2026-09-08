from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors import security
from repo_analyser.collectors.security import (
    _gitleaks_repo,
    _semgrep_repo,
    run_security,
)
from repo_analyser.core.util import RunResult


class TestGitleaksRepo:
    def test_parses_real_shaped_report_and_redacts_the_secret(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        def fake_run(cmd, **kwargs):
            report_path = Path(cmd[cmd.index("-r") + 1])
            report_path.write_text(json.dumps([{
                "RuleID": "generic-api-key", "File": "src/config.ts",
                "Commit": "abc123def456", "Author": "dev@example.com",
                "Date": "2024-01-01T00:00:00Z", "Secret": "sk_live_1234567890abcdef",
            }]))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(security, "run", fake_run)
        findings = _gitleaks_repo(repo, tmp_dir)
        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "generic-api-key"
        assert f.commit == "abc123def4"  # truncated to 10 chars
        assert f.secret_redacted == "sk_l...ef"  # never the raw secret
        assert "1234567890" not in f.secret_redacted

    def test_no_report_produced_returns_empty(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        monkeypatch.setattr(security, "run", lambda *a, **k: RunResult([], 0, "", ""))
        assert _gitleaks_repo(repo, tmp_dir) == []

    def test_short_secret_is_fully_masked_not_partially_leaked(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        def fake_run(cmd, **kwargs):
            report_path = Path(cmd[cmd.index("-r") + 1])
            report_path.write_text(json.dumps([{
                "RuleID": "short", "File": "f.ts", "Commit": "abc", "Author": "a",
                "Date": "2024-01-01", "Secret": "abc123",  # <= 8 chars
            }]))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(security, "run", fake_run)
        findings = _gitleaks_repo(repo, tmp_dir)
        assert findings[0].secret_redacted == "***"


class TestSemgrepRepo:
    def test_parses_real_shaped_output(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        def fake_run(cmd, **kwargs):
            report_path = Path(cmd[cmd.index("--output") + 1])
            report_path.write_text(json.dumps({
                "results": [{
                    "check_id": "javascript.lang.security.audit.sqli",
                    "path": "src/db.ts",
                    "start": {"line": 42},
                    "extra": {"severity": "ERROR", "message": "Possible SQL injection" * 20},
                }],
            }))
            return RunResult(cmd, 1, "", "")  # semgrep exits non-zero when it finds matches

        monkeypatch.setattr(security, "run", fake_run)
        findings = _semgrep_repo(repo, tmp_dir)
        assert len(findings) == 1
        assert findings[0].severity == "ERROR"
        assert findings[0].start_line == 42
        assert len(findings[0].message) <= 200  # truncated

    def test_no_report_returns_empty(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        monkeypatch.setattr(security, "run", lambda *a, **k: RunResult([], 1, "", ""))
        assert _semgrep_repo(repo, tmp_dir) == []


class TestRunSecurity:
    def test_a_repo_that_crashes_both_scanners_is_recorded_not_fatal(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()

        def always_raise(*a, **k):
            raise RuntimeError("tool not installed")

        monkeypatch.setattr(security, "run", always_raise)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        secrets_path, semgrep_path = run_security([repo], out_dir, tmp_path / "tmp")
        assert secrets_path.read_text().splitlines() == [
            "repo,rule_id,file,commit,author,date,secret_redacted"
        ]
        assert semgrep_path.read_text().splitlines() == [
            "repo,check_id,severity,file,start_line,message"
        ]
        errors = json.loads((out_dir / "security_errors.json").read_text())
        assert f"{repo.name}:gitleaks" in errors
        assert f"{repo.name}:semgrep" in errors

    def test_summary_counts_distinct_repos_with_secrets(self, tmp_path: Path, monkeypatch) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()

        def fake_run(cmd, **kwargs):
            if "gitleaks" in cmd[0]:
                report_path = Path(cmd[cmd.index("-r") + 1])
                report_path.write_text(json.dumps([{
                    "RuleID": "x", "File": "f", "Commit": "abc", "Author": "a",
                    "Date": "2024-01-01", "Secret": "0123456789abcdef",
                }]))
                return RunResult(cmd, 0, "", "")
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(security, "run", fake_run)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_security([repo_a, repo_b], out_dir, tmp_path / "tmp")
        summary = json.loads((out_dir / "security_summary.json").read_text())
        assert summary["total_secrets_found"] == 2
        assert summary["repos_with_secrets"] == 2
