from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.repo_type import POLYREPO_FLEET_MIN_SIZE, analyze_repo

from ._repo_type_helpers import _git_repo


class TestPrimaryTypePolyrepo:
    def test_catalog_info_yaml_registry(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "catalog-info.yaml").write_text("apiVersion: backstage.io/v1alpha1\nkind: Component\n")
        assert analyze_repo(repo, [repo]).primary_type == "polyrepo"

    def test_fleet_of_ten_plus_similarly_shaped_repos(self, tmp_path: Path) -> None:
        repos = []
        for i in range(POLYREPO_FLEET_MIN_SIZE):
            r = _git_repo(tmp_path / f"svc-{i}")
            (r / "package.json").write_text(json.dumps({"name": f"svc-{i}"}))
            repos.append(r)
        result = analyze_repo(repos[0], repos)
        assert result.primary_type == "polyrepo"

    def test_below_fleet_threshold_does_not_trigger_polyrepo(self, tmp_path: Path) -> None:
        repos = []
        for i in range(3):
            r = _git_repo(tmp_path / f"svc-{i}")
            (r / "package.json").write_text(json.dumps({"name": f"svc-{i}"}))
            repos.append(r)
        result = analyze_repo(repos[0], repos)
        assert result.primary_type == "single_repo"
