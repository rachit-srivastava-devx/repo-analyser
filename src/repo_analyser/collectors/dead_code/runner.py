"""dead_code collector entry point: `run_dead_code(repos, out_dir) -> Path`,
same shape as every other collector's `run_x` function. Writes a per-repo
summary CSV, a capped per-finding detail CSV, and a portfolio summary JSON.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import run_concurrent, write_csv, write_json
from .analyze import analyze_repo
from .models import DeadCodeResult

SUMMARY_FIELDS = ["repo", "dead_code_items_python", "unreferenced_export_count_js",
                  "finding_count", "tool_unavailable"]
FINDING_FIELDS = ["repo", "language", "kind", "file", "line", "name"]


def _summary_row(r: DeadCodeResult) -> dict:
    return {
        "repo": r.repo,
        "dead_code_items_python": r.dead_code_items_python,
        "unreferenced_export_count_js": r.unreferenced_export_count_js,
        "finding_count": len(r.findings),
        "tool_unavailable": ";".join(r.tool_unavailable),
    }


def run_dead_code(repos: list[Path], out_dir: Path) -> Path:
    # each repo's own analysis is one I/O-bound subprocess call (vulture)
    # plus in-memory regex work, independent of every other repo -- see
    # core.util.run_concurrent's docstring.
    results = run_concurrent(repos, analyze_repo)

    out_path = out_dir / "dead_code.csv"
    write_csv(out_path, [_summary_row(r) for r in results], fieldnames=SUMMARY_FIELDS)

    finding_rows = [{"repo": r.repo, **asdict(f)} for r in results for f in r.findings]
    write_csv(out_dir / "dead_code_findings.csv", finding_rows,
              fieldnames=FINDING_FIELDS if finding_rows else None)

    py_checked = [r for r in results if r.dead_code_items_python is not None]
    js_checked = [r for r in results if r.unreferenced_export_count_js is not None]
    write_json(out_dir / "dead_code_summary.json", {
        "repos_total": len(results),
        "repos_with_python_checked": len(py_checked),
        "repos_with_js_checked": len(js_checked),
        "total_python_dead_code_items": sum(r.dead_code_items_python for r in py_checked),
        "total_js_unreferenced_exports": sum(r.unreferenced_export_count_js for r in js_checked),
        "repos_with_tool_unavailable": {r.repo: r.tool_unavailable for r in results if r.tool_unavailable},
    })
    return out_path
