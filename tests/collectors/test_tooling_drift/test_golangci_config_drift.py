from __future__ import annotations

from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestGolangciConfigDrift:
    def test_one_go_mod_dir_has_golangci_yml_sibling_does_not(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "svc-a").mkdir()
        (repo / "svc-a" / "go.mod").write_text("module example.com/svc-a\n\ngo 1.21\n")
        (repo / "svc-a" / ".golangci.yml").write_text("linters:\n  enable:\n    - govet\n")
        (repo / "svc-b").mkdir()
        (repo / "svc-b" / "go.mod").write_text("module example.com/svc-b\n\ngo 1.21\n")

        rows = analyze_repo(repo)
        golangci_rows = [r for r in rows if r.config_kind == "golangci"]
        assert len(golangci_rows) == 1
        assert golangci_rows[0].packages_with_drift == 1
