from __future__ import annotations

import csv
from pathlib import Path

from repo_analyser.synthesis.deep_reports import repo_analysis


def _write_inventory_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["repo", "tier", "total_commits", "unique_authors", "bus_factor_gini",
                  "top_author", "top_author_share", "staleness_band"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _row(repo: str, band: str, tier: str = "active") -> dict:
    return {
        "repo": repo, "tier": tier, "total_commits": "10", "unique_authors": "2",
        "bus_factor_gini": "0.2", "top_author": "alice@example.com",
        "top_author_share": "0.6", "staleness_band": band,
    }


class TestRepoAnalysisStalenessBand:
    def test_missing_inventory_csv_returns_placeholder(self, tmp_path: Path) -> None:
        result = repo_analysis(tmp_path, tmp_path / "charts", "acme")
        assert "No inventory.csv found" in result

    def test_band_table_counts_repos_by_band(self, tmp_path: Path) -> None:
        _write_inventory_csv(tmp_path / "inventory.csv", [
            _row("fresh-repo", "fresh"),
            _row("aging-repo", "aging"),
            _row("stale-repo", "stale"),
            _row("abandoned-repo", "abandoned"),
        ])
        result = repo_analysis(tmp_path, tmp_path / "charts", "acme")
        assert "Lifecycle staleness band" in result
        # each band appears with a count of exactly 1 -- one row per band above
        for band in ("Fresh", "Aging", "Stale", "Abandoned"):
            assert band in result
        assert "Unknown" not in result  # no row lacked a band -- no unknown bucket shown

    def test_unknown_bucket_shown_only_when_a_row_has_no_band(self, tmp_path: Path) -> None:
        _write_inventory_csv(tmp_path / "inventory.csv", [
            _row("fresh-repo", "fresh"),
            _row("no-commits-repo", ""),  # write_csv renders a Python None as "" in the CSV
        ])
        result = repo_analysis(tmp_path, tmp_path / "charts", "acme")
        assert "Unknown" in result
        assert "missing/unusable last-commit data" in result

    def test_multiple_repos_in_same_band_are_counted_together(self, tmp_path: Path) -> None:
        _write_inventory_csv(tmp_path / "inventory.csv", [
            _row("repo-a", "abandoned"), _row("repo-b", "abandoned"), _row("repo-c", "fresh"),
        ])
        result = repo_analysis(tmp_path, tmp_path / "charts", "acme")
        # parse the rendered github-markdown table cell-by-cell rather than
        # assuming tabulate's exact column padding/whitespace.
        counts_by_band = {}
        for line in result.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] in ("Fresh", "Aging", "Stale", "Abandoned"):
                counts_by_band[cells[0]] = cells[2]
        assert counts_by_band["Abandoned"] == "2"
        assert counts_by_band["Fresh"] == "1"
