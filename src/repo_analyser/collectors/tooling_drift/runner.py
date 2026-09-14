"""Portfolio-level entrypoint: writes one CSV row per drift finding plus a
portfolio summary JSON.

Keeps a plain `repo` column, like every other collector's output, so
per-repo filtering works the same way it does for every other CSV this
tool writes.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .cross_repo_analyze import run_cross_repo_lint_drift
from .models import ToolingDriftRow


def run_tooling_drift(repos: list[Path], out_dir: Path) -> Path:
    all_rows: list[ToolingDriftRow] = []
    for repo in repos:
        all_rows.extend(analyze_repo(repo))

    cross_repo_rows, cross_repo_summaries = run_cross_repo_lint_drift(repos)
    all_rows.extend(cross_repo_rows)

    out_path = out_dir / "tooling_drift.csv"
    # Fieldnames are always passed explicitly (unlike deps_audit.py's
    # `None`-when-empty precedent) so the CSV keeps a header even when a
    # whole portfolio run produces zero rows -- a strictly more useful
    # empty-case than an empty file, and no contract requires matching
    # deps_audit.py's exact behavior here.
    write_csv(out_path, [asdict(r) for r in all_rows],
              fieldnames=list(ToolingDriftRow.__annotations__.keys()))

    drifted_repos = {r.repo for r in all_rows if r.config_kind != "none"}
    skipped_repos = {r.repo for r in all_rows if r.config_kind == "none"}
    write_json(out_dir / "tooling_drift_summary.json", {
        "repos_total": len(repos),
        "repos_with_drift": len(drifted_repos),
        "repos_skipped_insufficient_manifests": len(skipped_repos),
        "drift_rows_by_kind": dict(Counter(r.config_kind for r in all_rows if r.config_kind != "none")),
        # Portfolio-wide canonical fingerprint per cross-repo lint kind,
        # populated even when zero repos drifted (see cross_repo_drift.py).
        "cross_repo_canonical": {
            s.config_kind: {
                "canonical_fingerprint": s.canonical_fingerprint,
                "repos_compared": s.repos_compared,
                "repos_drifted": s.repos_drifted,
                "skipped_reason": s.skipped_reason,
            }
            for s in cross_repo_summaries
        },
    })
    return out_path
