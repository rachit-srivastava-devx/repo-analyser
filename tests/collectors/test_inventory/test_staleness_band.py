from __future__ import annotations

import pytest

from repo_analyser.collectors.inventory.staleness_band import staleness_band


class TestStalenessBand:
    @pytest.mark.parametrize("days,expected", [
        (0, "fresh"), (29, "fresh"),
        (30, "aging"), (90, "aging"),
        (91, "stale"), (365, "stale"),
        (366, "abandoned"), (5000, "abandoned"),
    ])
    def test_boundaries(self, days: int, expected: str) -> None:
        assert staleness_band(days) == expected

    def test_none_input_yields_none_not_a_crash_or_default_band(self) -> None:
        # a repo with zero commits / unset last-commit value must propagate
        # None rather than silently defaulting into e.g. "abandoned".
        assert staleness_band(None) is None
