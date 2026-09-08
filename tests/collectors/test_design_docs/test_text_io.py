from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.design_docs.text_io import join_sample, read_text_safe

from ._design_docs_helpers import write_bytes


def test_join_sample_under_cap() -> None:
    assert join_sample(["a", "b"], 5) == "a;b"


def test_join_sample_truncates_with_suffix() -> None:
    items = [str(i) for i in range(10)]
    result = join_sample(items, 3)
    assert result == "0;1;2;+7 more"


def test_read_text_safe_non_utf8_reports_error(tmp_path: Path) -> None:
    p = write_bytes(tmp_path, "bad.md", b"\xff\xfe\x00garbage")
    text, err = read_text_safe(p)
    assert text is None
    assert err is not None and "not valid UTF-8" in err


def test_read_text_safe_missing_file_reports_error(tmp_path: Path) -> None:
    text, err = read_text_safe(tmp_path / "does-not-exist.md")
    assert text is None
    assert err is not None and "unreadable" in err
