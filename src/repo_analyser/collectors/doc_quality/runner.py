"""Portfolio-level entrypoint: writes one CSV row per repo plus a summary
JSON. interrogate's real % and eslint-plugin-jsdoc's presence-only signal
are kept separate on purpose -- averaging a measured percentage with a
presence flag would be exactly the "averaging two different measurements"
anti-pattern AGENTS.md calls out (duplication.py vs exact_duplicates.py)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import DocQualityResult


def run_doc_quality(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "doc_quality.csv"
    write_csv(out_path, rows, fieldnames=DocQualityResult)

    interrogate_measured = [r for r in rows if r["doc_comment_tool"] == "interrogate"]
    write_json(out_dir / "doc_quality_summary.json", {
        "repos_total": len(rows),
        "repos_with_measured_python_doc_coverage": len(interrogate_measured),
        "mean_python_doc_comment_coverage_pct": (
            round(sum(r["doc_comment_coverage_pct"] for r in interrogate_measured) / len(interrogate_measured), 1)
            if interrogate_measured else None
        ),
        "repos_with_eslint_jsdoc_signal": sum(1 for r in rows if r["doc_comment_tool"] == "eslint-plugin-jsdoc"),
        "repos_with_changelog": sum(1 for r in rows if r["has_changelog"]),
        "repos_with_stale_changelog": sum(1 for r in rows if r["changelog_stale_vs_latest_tag"] == "stale"),
        "repos_with_unknown_changelog_staleness":
            sum(1 for r in rows if r["changelog_stale_vs_latest_tag"] == "unknown"),
    })
    return out_path
