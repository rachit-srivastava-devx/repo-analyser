from __future__ import annotations

import pytest

from repo_analyser.collectors.inventory.tiering import _gini, _tier


class TestTier:
    @pytest.mark.parametrize("days,expected", [
        (0, "active"), (90, "active"),
        (91, "recent"), (365, "recent"),
        (366, "aging"), (1095, "aging"),
        (1096, "dormant"), (5000, "dormant"),
    ])
    def test_boundaries(self, days: int, expected: str) -> None:
        assert _tier(days) == expected


class TestGini:
    def test_empty_is_zero(self) -> None:
        assert _gini([]) == 0.0

    def test_all_zero_is_zero_not_division_error(self) -> None:
        assert _gini([0, 0, 0]) == 0.0

    def test_perfectly_equal_authorship_is_zero(self) -> None:
        assert _gini([5, 5, 5, 5]) == 0.0

    def test_single_author_is_zero(self) -> None:
        # one author, 100% share -- Gini of a single-element distribution
        # is 0 by definition (there's no inequality *between* authors).
        assert _gini([42]) == 0.0

    def test_more_unequal_scores_higher(self) -> None:
        moderate = _gini([1, 3])
        extreme = _gini([1, 100])
        assert 0 < moderate < extreme < 1

    def test_known_value_two_authors_1_and_3(self) -> None:
        # G = (2*sum((i+1)*x_i))/(n*sum(x_i)) - (n+1)/n, sorted [1,3]:
        # cum = 1*1 + 2*3 = 7; G = 14/(2*4) - 3/2 = 1.75 - 1.5 = 0.25
        assert _gini([1, 3]) == 0.25

    def test_order_of_input_does_not_matter(self) -> None:
        assert _gini([3, 1, 5]) == _gini([5, 3, 1]) == _gini([1, 3, 5])
