from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_analyser.collectors import deps_audit
from repo_analyser.collectors.deps_audit import (
    LICENSE_ALLOWLIST,
    CVEFinding,
    LicenseFinding,
    OutdatedPackage,
    _audit_one_repo,
    _go_licenses_go,
    _go_outdated,
    _license_checker_js,
    _npm_outdated,
    _osv_scan,
    _pip_licenses_py,
    _pip_outdated,
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
        assert outdated[0].ecosystem == "js"
        assert outdated[0].current == "4.17.20"
        assert outdated[0].latest == "5.0.0"

    def test_malformed_json_output_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "not json{{{", ""))
        assert _npm_outdated(repo) == []


class TestPipOutdated:
    def test_no_python_markers_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _pip_outdated(repo) == ([], "")
        assert called == []

    def test_python_repo_without_venv_is_skip_reason_not_silent_empty(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        findings, skip = _pip_outdated(repo)
        assert findings == []
        assert skip  # non-empty: this is a real precondition-not-met, not "genuinely found nothing"

    def test_parses_real_shaped_pip_list_outdated_json(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        venv_bin = repo / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip").write_text("#!/bin/sh\n")
        fake_output = json.dumps([{"name": "requests", "version": "2.0.0", "latest_version": "2.31.0"}])
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _pip_outdated(repo)
        assert skip == ""
        assert len(findings) == 1
        assert findings[0] == OutdatedPackage(repo="repo", ecosystem="python", package="requests",
                                                current="2.0.0", wanted="2.0.0", latest="2.31.0")

    def test_empty_stdout_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "setup.py").write_text("")
        venv_bin = repo / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "", ""))
        assert _pip_outdated(repo) == ([], "")

    def test_malformed_json_output_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        venv_bin = repo / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "not json{{{", ""))
        assert _pip_outdated(repo) == ([], "")


class TestGoOutdated:
    def test_no_go_mod_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _go_outdated(repo) == ([], "")
        assert called == []

    def test_go_not_on_path_is_skip_reason(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: None)
        findings, skip = _go_outdated(repo)
        assert findings == []
        assert skip

    def test_exit_1_empty_stdout_toolchain_skew_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        # live-confirmed real shape: `go list -u -m -json all` exits 1 with
        # empty stdout when the repo's go.mod declares a newer `go`
        # directive than this machine can resolve.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.30\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go")
        monkeypatch.setattr(deps_audit, "run",
                             lambda *a, **k: RunResult([], 1, "", "go: download go1.30: toolchain not available"))
        assert _go_outdated(repo) == ([], "")

    def test_parses_real_shaped_concatenated_json_objects(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go")
        # real shape: pretty-printed JSON objects concatenated with no
        # separator -- the main module (no "Update" field, "Main": true)
        # followed by one dependency with an available update and one
        # already-current dependency (no "Update" field at all).
        fake_output = (
            '{\n\t"Path": "example.com/testrepo",\n\t"Main": true,\n\t"GoVersion": "1.21"\n}\n'
            '{\n\t"Path": "github.com/pkg/errors",\n\t"Version": "v0.8.0",\n'
            '\t"Update": {\n\t\t"Path": "github.com/pkg/errors",\n\t\t"Version": "v0.9.1"\n\t}\n}\n'
            '{\n\t"Path": "github.com/up-to-date/x",\n\t"Version": "v1.0.0"\n}\n'
        )
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _go_outdated(repo)
        assert skip == ""
        assert findings == [OutdatedPackage(repo="repo", ecosystem="go", package="github.com/pkg/errors",
                                              current="v0.8.0", wanted="v0.8.0", latest="v0.9.1")]

    def test_truncated_json_mid_stream_stops_cleanly_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        # a subprocess killed mid-write (AGENTS.md SS3 rung 3: "truncated
        # JSON from a killed subprocess") -- the first object parses fine,
        # the second is cut off. raw_decode must not raise past the loop.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go")
        fake_output = (
            '{\n\t"Path": "example.com/testrepo",\n\t"Main": true\n}\n'
            '{\n\t"Path": "github.com/pkg/errors",\n\t"Version": "v0.8.0",\n\t"Update": {'
        )
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _go_outdated(repo)
        assert skip == ""
        assert findings == []


class TestLicenseCheckerJs:
    def test_no_package_json_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _license_checker_js(repo) == ([], "")
        assert called == []

    def test_missing_local_binary_is_skip_reason_not_silent_empty(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        findings, skip = _license_checker_js(repo)
        assert findings == []
        assert skip

    def test_excludes_own_package_by_path_and_flags_violation(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        bin_dir = repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "license-checker").write_text("")
        fake_output = json.dumps({
            "repo@1.0.0": {"licenses": "UNKNOWN", "path": str(repo)},
            "left-pad@1.3.0": {"licenses": "WTFPL", "path": str(repo / "node_modules" / "left-pad")},
            "lodash@4.17.21": {"licenses": "MIT", "path": str(repo / "node_modules" / "lodash")},
        })
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _license_checker_js(repo)
        assert skip == ""
        by_pkg = {f.package: f for f in findings}
        assert "repo" not in by_pkg  # own package excluded by path, not name
        assert by_pkg["left-pad"] == LicenseFinding(repo="repo", ecosystem="js", package="left-pad",
                                                       license="WTFPL", license_violation=True)
        assert by_pkg["lodash"].license_violation is False

    def test_list_licenses_joined_with_or(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        bin_dir = repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "license-checker").write_text("")
        fake_output = json.dumps({
            "dual@1.0.0": {"licenses": ["MIT", "Apache-2.0"], "path": str(repo / "node_modules" / "dual")},
        })
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, _skip = _license_checker_js(repo)
        assert findings[0].license == "MIT OR Apache-2.0"

    def test_empty_stdout_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        bin_dir = repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "license-checker").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "", ""))
        assert _license_checker_js(repo) == ([], "")

    def test_malformed_json_output_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        bin_dir = repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "license-checker").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "not json{{{", ""))
        assert _license_checker_js(repo) == ([], "")


class TestPipLicensesPy:
    def test_no_python_markers_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _pip_licenses_py(repo) == ([], "")
        assert called == []

    def test_python_repo_without_venv_is_skip_reason(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        findings, skip = _pip_licenses_py(repo)
        assert findings == []
        assert skip

    def test_classifier_text_normalized_via_alias_table(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\nsomepkg==1.0\nleft-pad==1.0\n")
        venv_bin = repo / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip-licenses").write_text("")
        # real shape confirmed live: pip-licenses --format=json output.
        # `somepkg` here is a synthetic package, not real -- it exists only
        # to test the "already an exact allow-listed SPDX id, no alias
        # needed" pass-through path in isolation. It is NOT a claim about
        # what any real package's pip-licenses output looks like; `idna`'s
        # real output is "BSD License" (the bare, ambiguous form), covered
        # by the `left-pad` row below instead.
        fake_output = json.dumps([
            {"License": "Apache Software License", "Name": "requests", "Version": "2.34.2"},
            {"License": "BSD-3-Clause", "Name": "somepkg", "Version": "1.0"},
            {"License": "BSD License", "Name": "left-pad", "Version": "1.0"},
        ])
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _pip_licenses_py(repo)
        assert skip == ""
        by_pkg = {f.package: f for f in findings}
        assert by_pkg["requests"].license == "Apache-2.0"  # aliased from classifier text
        assert by_pkg["requests"].license_violation is False
        assert by_pkg["somepkg"].license == "BSD-3-Clause"  # already exact, no alias needed
        assert by_pkg["somepkg"].license_violation is False
        # "BSD License" alone doesn't say 2- vs 3-clause -- deliberately
        # left unmapped, so it is flagged rather than silently guessed.
        assert by_pkg["left-pad"].license == "BSD License"
        assert by_pkg["left-pad"].license_violation is True

    def test_malformed_json_output_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        venv_bin = repo / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip-licenses").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "not json{{{", ""))
        assert _pip_licenses_py(repo) == ([], "")

    def test_empty_stdout_returns_empty_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        venv_bin = repo / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "pip-licenses").write_text("")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "", ""))
        assert _pip_licenses_py(repo) == ([], "")


class TestGoLicensesGo:
    def test_no_go_mod_returns_empty_without_invoking_tool(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        called = []
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: called.append(1) or RunResult([], 0, "", ""))
        assert _go_licenses_go(repo) == ([], "")
        assert called == []

    def test_tool_not_on_path_is_skip_reason(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: None)
        findings, skip = _go_licenses_go(repo)
        assert findings == []
        assert skip

    def test_a_genuine_tool_crash_raises_not_silently_empty(self, tmp_path: Path, monkeypatch) -> None:
        # live-confirmed on this machine: a go-licenses binary that
        # crashes (macOS dyld "missing LC_UUID load command", exit 134,
        # empty stdout) must propagate as a real failure, not "no
        # licenses found" -- check=True is the default and is not
        # overridden for this call.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go-licenses")

        def fake_run(cmd, **kwargs):
            from repo_analyser.core.util import ToolExecutionError
            raise ToolExecutionError(cmd, 134, "dyld: missing LC_UUID load command")

        monkeypatch.setattr(deps_audit, "run", fake_run)
        with pytest.raises(Exception):  # noqa: B017 -- ToolExecutionError specifically, imported above
            _go_licenses_go(repo)

    def test_parses_real_shaped_headerless_csv(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go-licenses")
        fake_output = (
            "github.com/pkg/errors,https://github.com/pkg/errors/blob/master/LICENSE,BSD-2-Clause\n"
            "github.com/gpl-thing/x,https://example.com/LICENSE,GPL-3.0\n"
        )
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _go_licenses_go(repo)
        assert skip == ""
        by_pkg = {f.package: f for f in findings}
        assert by_pkg["github.com/pkg/errors"].license == "BSD-2-Clause"
        assert by_pkg["github.com/pkg/errors"].license_violation is False
        assert by_pkg["github.com/gpl-thing/x"].license_violation is True

    def test_malformed_row_wrong_column_count_is_skipped_not_crash(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go-licenses")
        fake_output = (
            "github.com/pkg/errors,https://example.com/LICENSE,BSD-2-Clause\n"
            "a-row,with,too,many,columns\n"
        )
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, fake_output, ""))
        findings, skip = _go_licenses_go(repo)
        assert skip == ""
        assert [f.package for f in findings] == ["github.com/pkg/errors"]


class TestAuditOneRepoErrorIsolation:
    def test_every_new_signal_crashing_is_caught_independently(self, tmp_path: Path, monkeypatch) -> None:
        # a real risk of adding 5 near-identical try/except blocks by hand:
        # a copy-paste mistake wiring the wrong dict key, or forgetting one
        # entirely, so that one signal's crash silently drops another's
        # result or aborts the whole repo scan. Every precondition below is
        # satisfied so each of the 5 new sub-scans actually calls `run()`
        # (not short-circuited to [] before ever reaching the failing call),
        # and `run` always raises -- if any except block were missing or
        # mis-keyed, either this raises out of `_audit_one_repo` (it
        # currently doesn't -- see the existing osv-scanner/npm-outdated
        # precedent) or one of the 5 expected error keys goes missing below.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        (repo / "node_modules" / ".bin").mkdir(parents=True)
        (repo / "node_modules" / ".bin" / "license-checker").write_text("")
        (repo / ".venv" / "bin").mkdir(parents=True)
        (repo / ".venv" / "bin" / "pip").write_text("")
        (repo / ".venv" / "bin" / "pip-licenses").write_text("")
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: "/usr/bin/go-licenses")
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

        cves, outdated, licenses, errors, skips = _audit_one_repo(repo)

        assert cves == []
        assert outdated == []
        assert licenses == []
        for key in ("osv-scanner", "npm-outdated", "pip-outdated", "go-outdated",
                    "license-checker", "pip-licenses", "go-licenses"):
            assert f"repo:{key}" in errors, f"missing error for {key}"
        assert skips == {}  # every precondition was satisfied -- these are real crashes, not skips


class TestLicenseAllowlist:
    def test_allowlist_is_the_five_documented_licenses(self) -> None:
        # locks the exact set docs/ROADMAP.md specifies -- a future
        # deps_diff.py must reuse this constant rather than diverge.
        assert LICENSE_ALLOWLIST == frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"})


class TestRunDepsAudit:
    def test_empty_repo_list_writes_valid_empty_outputs(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        cve_path = run_deps_audit([], out_dir)
        assert cve_path.read_text().splitlines() == [
            "repo,source,package,severity,id,fix_available"
        ]
        assert (out_dir / "deps_outdated.csv").read_text().splitlines() == [
            "repo,ecosystem,package,current,wanted,latest"
        ]
        assert (out_dir / "deps_licenses.csv").read_text().splitlines() == [
            "repo,ecosystem,package,license,license_violation"
        ]
        summary = json.loads((out_dir / "deps_audit_summary.json").read_text())
        assert summary["total_cve_findings"] == 0
        assert summary["outdated_major_version_behind"] == 0
        assert summary["total_license_findings"] == 0
        assert summary["license_violations"] == 0
        assert summary["repos_with_license_violations"] == 0
        # empty repo list -> no skip reasons to report at all (never a
        # dangling deps_audit_skips.json for a run that had nothing to skip)
        assert not (out_dir / "deps_audit_skips.json").exists()

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

    def test_license_violations_end_to_end_via_js_dependency(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        bin_dir = repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "license-checker").write_text("")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        lc_output = json.dumps({
            "left-pad@1.3.0": {"licenses": "WTFPL", "path": str(repo / "node_modules" / "left-pad")},
            "lodash@4.17.21": {"licenses": "MIT", "path": str(repo / "node_modules" / "lodash")},
        })

        def fake_run(cmd, **kwargs):
            if "license-checker" in cmd[0]:
                return RunResult(cmd, 0, lc_output, "")
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(deps_audit, "run", fake_run)
        run_deps_audit([repo], out_dir)
        rows = (out_dir / "deps_licenses.csv").read_text().splitlines()
        assert "repo,js,left-pad,WTFPL,True" in rows
        assert "repo,js,lodash,MIT,False" in rows
        summary = json.loads((out_dir / "deps_audit_summary.json").read_text())
        assert summary["total_license_findings"] == 2
        assert summary["license_violations"] == 1
        assert summary["repos_with_license_violations"] == 1
        assert summary["repos_with_license_violations_list"] == ["repo"]

    def test_skip_reasons_surfaced_in_deps_audit_skips_json(self, tmp_path: Path, monkeypatch) -> None:
        # a JS+Python+Go repo with none of the 5 license/staleness tools'
        # local preconditions met -- verifies `_audit_one_repo` actually
        # wires each sub-scan's own skip_reason through to the shared
        # `skips` dict under its own key (a real risk with 5 near-identical
        # blocks: one gets the wrong dict key, or its `if skip:` body
        # dropped, and its skip goes missing silently).
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text("{}")
        (repo / "requirements.txt").write_text("requests==2.0.0\n")
        (repo / "go.mod").write_text("module x\n\ngo 1.21\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        monkeypatch.setattr(deps_audit.shutil, "which", lambda *_a: None)
        monkeypatch.setattr(deps_audit, "run", lambda *a, **k: RunResult([], 0, "", ""))
        run_deps_audit([repo], out_dir)
        skips = json.loads((out_dir / "deps_audit_skips.json").read_text())
        for key in ("license-checker", "pip-outdated", "go-outdated", "pip-licenses", "go-licenses"):
            assert f"repo:{key}" in skips, f"missing skip_reason for {key}"
