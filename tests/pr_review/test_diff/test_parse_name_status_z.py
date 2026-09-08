"""Tests for pr_review.name_status._parse_name_status_z."""
from __future__ import annotations

from repo_analyser.pr_review.name_status import _parse_name_status_z


class TestParseNameStatusZ:
    def test_simple_add_and_modify(self) -> None:
        raw = "A\0new.txt\0M\0changed.txt\0"
        assert _parse_name_status_z(raw) == [
            ("A", "new.txt", None),
            ("M", "changed.txt", None),
        ]

    def test_rename_with_similarity_score(self) -> None:
        raw = "R100\0old_name.txt\0new_name.txt\0"
        assert _parse_name_status_z(raw) == [("R", "new_name.txt", "old_name.txt")]

    def test_deletion(self) -> None:
        raw = "D\0gone.txt\0"
        assert _parse_name_status_z(raw) == [("D", "gone.txt", None)]

    def test_empty_input(self) -> None:
        assert _parse_name_status_z("") == []
