from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_analyser.collectors import deps_audit
from repo_analyser.collectors.deps_audit import (
    CVEFinding,
    _npm_outdated,
    _osv_scan,
    _severity_tier,
    run_deps_audit,
)
from repo_analyser.core.util import RunResult


class TestSeverityTier:
    @pytest.mark.parametrize("score,expected", [
        ("9.8", "critical"), ("9.0", "critical"),
        ("8.9", "high"), ("7.0", "high"),
        ("6.9", "medium"), ("4.0", "medium"),
        ("3.9", "low"), ("0.0", "low"),
    ])
    def test_boundaries(self, score: str, expected: str) -> None:
        assert _severity_tier(score) == expected

    def test_non_numeric_is_unknown_not_a_crash(self) -> None:
        # osv-scanner really does emit the string "unknown" for some vulns.
        assert _severity_tier("unknown") == "unknown"

    def test_cvss_vector_string_is_unknown_not_a_crash(self) -> None:
        # the historical bug: a full CVSS vector string, not a numeric
        # score, ending up in this field. float() rejects it cleanly.
        assert _severity_tier("CVSS:3.1/AV:L/AC:L/PR:N") == "unknown"

    def test_empty_string_is_unknown(self) -> None:
        assert _severity_tier("") == "unknown"


class TestOsvScan:
    def test_no_lockfiles_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "no_lockfile_repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _osv_scan(repo) == []
        assert called == []  # the whole point: skip the subprocess call entirely

    def test_malformed_json_output_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "not json{{{", ""))
        assert _osv_scan(repo) == []

    def test_parses_real_shaped_output_using_max_severity_not_vector_string(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        fake_output = json.dumps({
            "results": [{
                "packages": [{
                    "package": {"name": "lodash"},
                    "groups": [{"ids": ["GHSA-xxxx"], "max_severity": "7.5"}],
                    "vulnerabilities": [{
                        "id": "GHSA-xxxx",
                        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
                    }],
                }],
            }],
        })
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings = _osv_scan(repo)
        assert len(findings) == 1
        assert findings[0] == CVEFinding(
            repo="repo", source="osv-scanner", package="lodash", severity="7.5",
            id="GHSA-xxxx", fix_available="unknown",
        )
        assert _severity_tier(findings[0].severity) == "high"  # not "unknown" from the vector string

    def test_finding_with_no_matching_group_severity_is_unknown(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package-lock.json").write_text("{}")
        fake_output = json.dumps({
            "results": [{"packages": [{
                "package": {"name": "leftpad"},
                "groups": [],
                "vulnerabilities": [{"id": "GHSA-yyyy", "severity": []}],
            }]}],
        })
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings = _osv_scan(repo)
        assert findings[0].severity == "unknown"


class TestNpmOutdated:
    def test_no_package_json_returns_empty(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        assert _npm_outdated(repo) == []

    def test_parses_real_shaped_npm_outdated_json(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        fake_output = json.dumps({"lodash": {"current": "4.17.20", "wanted": "4.17.21", "latest": "5.0.0"}})
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        outdated = _npm_outdated(repo)
        assert len(outdated) == 1
        assert outdated[0].package == "lodash"
        assert outdated[0].current == "4.17.20"
        assert outdated[0].latest == "5.0.0"


class TestRunDepsAudit:
    def test_empty_repo_list_writes_valid_empty_outputs(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        cve_path = run_deps_audit([], out_dir)
        assert cve_path.read_text().splitlines() == [
            "repo,source,package,severity,id,fix_available"
        ]
        assert (out_dir / "deps_outdated.csv").read_text().splitlines() == [
            "repo,package,current,wanted,latest"
        ]
        summary = json.loads((out_dir / "deps_audit_summary.json").read_text())
        assert summary["total_cve_findings"] == 0
        assert summary["outdated_major_version_behind"] == 0

    def test_major_version_behind_uses_first_segment_only(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        def fake_run(cmd, **kwargs):
            if cmd[0] == "osv-scanner":
                return RunResult(cmd, 0, "", "")
            return RunResult(cmd, 0, json.dumps({
                "same-major": {"current": "4.1.0", "wanted": "4.2.0", "latest": "4.9.0"},
                "major-behind": {"current": "1.0.0", "wanted": "1.0.0", "latest": "3.0.0"},
            }), "")

        monkeypatch.setattr(deps_audit, "run", fake_run)
        run_deps_audit([repo], out_dir)
        summary = json.loads((out_dir / "deps_audit_summary.json").read_text())
        assert summary["total_outdated_packages"] == 2
        assert summary["outdated_major_version_behind"] == 1

    def test_a_repo_whose_scan_raises_does_not_abort_the_whole_run(self, tmp_path: Path, monkeypatch) -> None:
        good_repo = tmp_path / "good"
        good_repo.mkdir()
        bad_repo = tmp_path / "bad"
        bad_repo.mkdir()
        (bad_repo / "package-lock.json").write_text("{}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # osv-scanner is invoked with the repo path as a positional cmd arg.
        def fake_run(cmd, **kwargs):
            if any("bad" in str(c) for c in cmd):
                raise RuntimeError("simulated tool crash")
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(deps_audit, "run", fake_run)
        cve_path = run_deps_audit([good_repo, bad_repo], out_dir)
        assert cve_path.exists()
        errors = json.loads((out_dir / "deps_audit_errors.json").read_text())
        assert any("bad" in k for k in errors)
