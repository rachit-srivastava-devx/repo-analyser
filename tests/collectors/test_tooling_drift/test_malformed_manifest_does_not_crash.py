from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestMalformedManifestDoesNotCrash:
    def test_malformed_package_json_among_valid_ones_does_not_crash(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^3.0.0"}}))
        (repo / "pkg-c").mkdir()
        (repo / "pkg-c" / "package.json").write_text("{not valid json")

        rows = analyze_repo(repo)  # must not raise

        drift_rows = [r for r in rows if r.config_kind == "dependency_version"]
        assert len(drift_rows) == 1
        # the malformed manifest contributes zero dependencies -- it
        # doesn't silently zero out or corrupt the real comparison
        # between pkg-a and pkg-b.
        assert drift_rows[0].packages_compared == 1
        assert "lodash@^4.17.0" in drift_rows[0].drift_detail
        assert "lodash@^3.0.0" in drift_rows[0].drift_detail

    def test_empty_manifest_files_do_not_crash(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text("")
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text("")

        rows = analyze_repo(repo)  # must not raise
        # both manifests parse to zero dependencies -- attempted, nothing
        # shared to compare, no drift; a real, clean empty result.
        assert rows == []

    def test_empty_pyproject_toml_and_empty_go_mod_do_not_crash(self, tmp_path: Path) -> None:
        # a manifest file that exists on disk but is zero bytes -- distinct
        # from "malformed" (invalid syntax) and from "absent" (file doesn't
        # exist at all). Both the [tool.ruff]-table regex scan and the
        # go.mod require-line scan must read this as "nothing declared",
        # not raise.
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "pyproject.toml").write_text("")
        (repo / "pkg-a" / "go.mod").write_text("")
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "pyproject.toml").write_text("")
        (repo / "pkg-b" / "go.mod").write_text("")

        rows = analyze_repo(repo)  # must not raise
        assert rows == []  # both formats attempted (2 found each), nothing to compare, no drift

    def test_malformed_docker_compose_style_yaml_in_golangci_config_does_not_crash(self, tmp_path: Path) -> None:
        # a .golangci.yml that isn't even valid YAML must not crash content
        # hashing -- this module only hashes raw text, it never parses YAML.
        repo = _mkrepo(tmp_path)
        (repo / "svc-a").mkdir()
        (repo / "svc-a" / "go.mod").write_text("module example.com/svc-a\n")
        (repo / "svc-a" / ".golangci.yml").write_text(":::not valid yaml:::\n  -\n")
        (repo / "svc-b").mkdir()
        (repo / "svc-b" / "go.mod").write_text("module example.com/svc-b\n")

        rows = analyze_repo(repo)  # must not raise
        assert any(r.config_kind == "golangci" for r in rows)
