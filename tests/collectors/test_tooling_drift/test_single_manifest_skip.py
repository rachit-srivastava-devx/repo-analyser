from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestSingleManifestSkip:
    """A repo with only one manifest anywhere in the tree can't have
    drift by definition -- there's nothing to compare it against."""

    def test_single_package_json_reports_skip_reason(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        (repo / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        rows = analyze_repo(repo)
        assert len(rows) == 1
        assert rows[0].config_kind == "none"
        assert rows[0].skip_reason  # populated -- no comparison possible
        assert rows[0].packages_compared == 0
        assert rows[0].packages_with_drift == 0
        assert rows[0].drift_detail == ""

    def test_completely_manifest_free_repo_also_reports_skip_reason(self, tmp_path: Path) -> None:
        repo = _mkrepo(tmp_path)
        rows = analyze_repo(repo)
        assert len(rows) == 1
        assert rows[0].config_kind == "none"
        assert rows[0].skip_reason
