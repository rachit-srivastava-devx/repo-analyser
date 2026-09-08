from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.migration_hygiene.git_blobs import blob_content


def test_blob_content_returns_empty_on_oserror(tmp_path: Path) -> None:
    """A `cwd` that doesn't exist makes subprocess.run raise OSError before
    git even runs -- must degrade to b"", never crash the caller (mirrors
    a bad sha / git binary missing / any other real-world failure that
    can hit this same except clause)."""
    nonexistent_repo = tmp_path / "does_not_exist"
    assert blob_content(nonexistent_repo, "deadbeef") == b""
