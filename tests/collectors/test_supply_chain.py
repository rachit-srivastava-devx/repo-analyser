from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from repo_analyser.collectors import supply_chain
from repo_analyser.collectors.supply_chain import (
    _trivy_config_repo,
    _trivy_sbom_repo,
    run_supply_chain,
)
from repo_analyser.core.util import RunResult

HAS_TRIVY = shutil.which("trivy") is not None


class TestTrivyConfigRepo:
    def test_parses_real_shaped_report(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        def fake_run(cmd, **kwargs):
            report_path = Path(cmd[cmd.index("--output") + 1])
            report_path.write_text(json.dumps({
                "Results": [{
                    "Target": "Dockerfile",
                    "MisconfSummary": {"Successes": 24, "Failures": 1},
                    "Misconfigurations": [{
                        "ID": "DS-0002", "Title": "Image user should not be 'root'",
                        "Severity": "HIGH", "Message": "Last USER command should not be 'root'" * 10,
                        "Resolution": "Add 'USER <non root user name>' line to the Dockerfile",
                        "CauseMetadata": {"StartLine": 2, "EndLine": 2},
                    }],
                }],
            }))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(supply_chain, "run", fake_run)
        findings = _trivy_config_repo(repo, tmp_dir)
        assert len(findings) == 1
        f = findings[0]
        assert f.id == "DS-0002"
        assert f.severity == "HIGH"
        assert f.target == "Dockerfile"
        assert f.start_line == 2
        assert len(f.message) <= 200  # truncated

    def test_no_report_produced_returns_empty(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        monkeypatch.setattr(supply_chain, "run", lambda *a, **k: RunResult([], 0, "", ""))
        assert _trivy_config_repo(repo, tmp_dir) == []

    def test_clean_repo_with_only_successes_yields_no_findings(self, tmp_path: Path, monkeypatch) -> None:
        # Regression guard for the real, grounded behavior: trivy only itemizes
        # FAILED checks in `Misconfigurations` -- `MisconfSummary.Successes`
        # alone (no corresponding entries) must not be misread as findings.
        repo = tmp_path / "repo"
        repo.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        def fake_run(cmd, **kwargs):
            report_path = Path(cmd[cmd.index("--output") + 1])
            report_path.write_text(json.dumps({
                "Results": [{"Target": "Dockerfile",
                             "MisconfSummary": {"Successes": 24, "Failures": 0},
                             "Misconfigurations": []}],
            }))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(supply_chain, "run", fake_run)
        assert _trivy_config_repo(repo, tmp_dir) == []


class TestTrivySbomRepo:
    def test_counts_components_from_real_shaped_cyclonedx(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        sbom_dir = tmp_path / "sbom"
        sbom_dir.mkdir()

        def fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("--output") + 1])
            out_path.write_text(json.dumps({
                "bomFormat": "CycloneDX", "specVersion": "1.7",
                "components": [{"name": "package-lock.json", "type": "application"},
                                {"name": "lodash", "version": "4.17.21", "type": "library"}],
            }))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(supply_chain, "run", fake_run)
        path, count = _trivy_sbom_repo(repo, sbom_dir)
        assert path is not None
        assert path.exists()
        assert count == 2

    def test_no_lockfile_produces_no_sbom_not_a_crash(self, tmp_path: Path, monkeypatch) -> None:
        # Grounded against real trivy: a bare package.json with no lockfile
        # still produces a valid (empty-components) CycloneDX document.
        repo = tmp_path / "repo"
        repo.mkdir()
        sbom_dir = tmp_path / "sbom"
        sbom_dir.mkdir()

        def fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("--output") + 1])
            out_path.write_text(json.dumps({"bomFormat": "CycloneDX", "components": []}))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(supply_chain, "run", fake_run)
        path, count = _trivy_sbom_repo(repo, sbom_dir)
        assert path is not None
        assert count == 0

    def test_no_output_file_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        sbom_dir = tmp_path / "sbom"
        sbom_dir.mkdir()
        monkeypatch.setattr(supply_chain, "run", lambda *a, **k: RunResult([], 1, "", ""))
        path, count = _trivy_sbom_repo(repo, sbom_dir)
        assert path is None
        assert count == 0


class TestRunSupplyChain:
    def test_a_repo_that_crashes_both_scans_is_recorded_not_fatal(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()

        def always_raise(*a, **k):
            raise RuntimeError("tool not installed")

        monkeypatch.setattr(supply_chain, "run", always_raise)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        misconfig_path = run_supply_chain([repo], out_dir, tmp_path / "tmp")
        assert misconfig_path.read_text().splitlines() == [
            "repo,id,title,severity,target,start_line,message,resolution"
        ]
        errors = json.loads((out_dir / "supply_chain_errors.json").read_text())
        assert f"{repo.name}:trivy-config" in errors
        assert f"{repo.name}:trivy-sbom" in errors

    def test_summary_counts_and_sbom_dir_created(self, tmp_path: Path, monkeypatch) -> None:
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()

        def fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("--output") + 1])
            if "config" in cmd:
                out_path.write_text(json.dumps({
                    "Results": [{"Target": "Dockerfile", "Misconfigurations": [
                        {"ID": "DS-0002", "Severity": "HIGH", "Title": "t", "Message": "m",
                         "Resolution": "r", "CauseMetadata": {"StartLine": 1}},
                    ]}],
                }))
            else:
                out_path.write_text(json.dumps({"components": [{"name": "x", "type": "library"}]}))
            return RunResult(cmd, 0, "", "")

        monkeypatch.setattr(supply_chain, "run", fake_run)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_supply_chain([repo_a, repo_b], out_dir, tmp_path / "tmp")
        summary = json.loads((out_dir / "supply_chain_summary.json").read_text())
        assert summary["total_misconfigs"] == 2
        assert summary["repos_with_misconfigs"] == 2
        assert summary["repos_with_sbom_generated"] == 2
        assert (out_dir / "sbom").is_dir()


@pytest.mark.skipif(not HAS_TRIVY, reason="trivy not on PATH")
class TestRealTrivyExecution:
    def test_dockerfile_running_as_root_is_flagged_for_real(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Dockerfile").write_text(
            "FROM ubuntu:20.04\nUSER root\nRUN apt-get update\n"
        )
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_supply_chain([repo], out_dir, tmp_path / "tmp")
        rows = (out_dir / "supply_chain_misconfigs.csv").read_text()
        assert "DS-0002" in rows  # real finding ID from a real trivy run, not guessed

    def test_lockfile_produces_a_real_nonempty_sbom(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text('{"name": "p", "dependencies": {"lodash": "4.17.21"}}')
        (repo / "package-lock.json").write_text(json.dumps({
            "name": "p", "version": "1.0.0", "lockfileVersion": 3, "requires": True,
            "packages": {
                "": {"name": "p", "version": "1.0.0", "dependencies": {"lodash": "4.17.21"}},
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-abc123",
                },
            },
        }))
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_supply_chain([repo], out_dir, tmp_path / "tmp")
        sbom_files = list((out_dir / "sbom").glob("*.cyclonedx.json"))
        assert len(sbom_files) == 1
        data = json.loads(sbom_files[0].read_text())
        assert data["bomFormat"] == "CycloneDX"
        assert len(data["components"]) >= 1
