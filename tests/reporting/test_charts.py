"""Smoke tests for every chart function: real matplotlib rendering (Agg
backend, no display needed) with minimal synthetic data, asserting a real,
non-empty PNG lands at the declared output path.

Not pixel-level verification -- these exist because mutation testing this
tool ran on itself found charts.py at 0% test coverage (every one of 1018
mutants reported "no_coverage"), meaning a crash in any chart function
would have gone completely undetected. This closes that gap at the level
that matters most for rendering code: does it run end-to-end without
raising, and does it actually produce the artifact it promises.
"""
from __future__ import annotations

from pathlib import Path

from repo_analyser.reporting import charts


def _assert_real_png(path: Path) -> None:
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


class TestDualAxisTrend:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        result = charts.dual_axis_trend(
            ["2025-01", "2025-02", "2025-03"], [10, 20, 15], [0.1, 0.3, 0.2],
            "commits", "escape rate", "title", out, subtitle="sub",
        )
        assert result == out
        _assert_real_png(out)


class TestSingleLineTrend:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.single_line_trend(["a", "b", "c"], [1.0, 2.0, 3.0], "title", out)
        _assert_real_png(out)

    def test_warn_semantic_renders(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.single_line_trend(["a", "b"], [1.0, 2.0], "title", out, semantic="warn",
                                  ylabel="y", annotation="note")
        _assert_real_png(out)


class TestStackedShareBar:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.stacked_share_bar(
            ["2025-01", "2025-02"],
            {"delivery": [0.5, 0.6], "correction": [0.3, 0.2], "other": [0.2, 0.2]},
            "title", out,
        )
        _assert_real_png(out)

    def test_explicit_highlight_renders(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.stacked_share_bar(["2025-01"], {"a": [1.0]}, "title", out, highlight="a")
        _assert_real_png(out)


class TestLorenzCurve:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.lorenz_curve([0.1, 0.3, 0.6, 1.0], "title", out, gini=0.35, n_entities=4)
        _assert_real_png(out)


class TestHorizontalBarRanked:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.horizontal_bar_ranked(["repo-a", "repo-b"], [100, 50], "title", out)
        _assert_real_png(out)

    def test_single_bar_renders(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.horizontal_bar_ranked(["repo-a"], [1], "title", out)
        _assert_real_png(out)


class TestScatterPlot:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.scatter_plot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0], ["a", "b", "c"],
                             "title", out, "xlabel", "ylabel")
        _assert_real_png(out)


class TestNetworkClusters:
    def test_renders_a_real_png(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.network_clusters(
            ["a", "b", "c"], [("a", "b"), ("b", "c")], "title", out,
            node_size={"a": 10.0, "b": 20.0, "c": 5.0},
            node_color={"a": "#1E6FFF", "b": "#0A0A0A", "c": "#999999"},
        )
        _assert_real_png(out)

    def test_no_edges_renders_without_crashing(self, tmp_path: Path) -> None:
        out = tmp_path / "chart.png"
        charts.network_clusters(["a"], [], "title", out)
        _assert_real_png(out)
