from __future__ import annotations

import json
from pathlib import Path

from _tooling_drift_helpers import _mkrepo

from repo_analyser.collectors.tooling_drift import analyze_repo


class TestExcludedDirectories:
    def test_node_modules_manifests_are_never_compared(self, tmp_path: Path) -> None:
        # a package.json nested inside node_modules is a THIRD PARTY
        # manifest, not this repo's own -- it must never participate in a
        # drift comparison, however many sibling copies happen to exist
        # (npm can nest the same transitive dep at many different
        # versions on purpose; that is not this repo's own tooling drift).
        repo = _mkrepo(tmp_path)
        (repo / "pkg-a").mkdir()
        (repo / "pkg-a" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        (repo / "pkg-b").mkdir()
        (repo / "pkg-b" / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^4.17.0"}}))
        nested = repo / "pkg-a" / "node_modules" / "some-dep"
        nested.mkdir(parents=True)
        (nested / "package.json").write_text(json.dumps({"dependencies": {"lodash": "^0.0.1"}}))

        rows = analyze_repo(repo)
        # pkg-a and pkg-b agree (both ^4.17.0) -- the node_modules copy's
        # wildly different pinned version must not leak into the result.
        assert rows == []
