"""Tests for pr_review.numstat._parse_numstat_z."""
from __future__ import annotations

from repo_analyser.pr_review.numstat import _parse_numstat_z


class TestParseNumstatZ:
    def test_simple_add(self) -> None:
        raw = "3\t0\tnew.txt\0"
        assert _parse_numstat_z(raw) == {"new.txt": (3, 0)}

    def test_binary_file_maps_dash_to_zero(self) -> None:
        raw = "-\t-\timage.bin\0"
        assert _parse_numstat_z(raw) == {"image.bin": (0, 0)}

    def test_rename_nested_under_shared_prefix(self) -> None:
        # The exact case plain-text numstat abbreviates ambiguously as
        # "nested/deep/{old_name.txt => new_name.txt}" -- -z instead emits
        # an empty combined-path field followed by two separate,
        # unabbreviated NUL-terminated paths.
        raw = "0\t0\t\0nested/deep/old_name.txt\0nested/deep/new_name.txt\0"
        assert _parse_numstat_z(raw) == {"nested/deep/new_name.txt": (0, 0)}

    def test_empty_input(self) -> None:
        assert _parse_numstat_z("") == {}
