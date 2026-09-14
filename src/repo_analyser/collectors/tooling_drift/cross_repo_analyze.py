"""Portfolio-wide orchestration for the cross-repo lint/format
canonical-config dimension: runs `check_cross_repo_lint_drift` once per
lint kind, reusing `LINT_KIND_SPECS` -- the exact same (kind, filename,
display_fn) registry lint_drift.py already defines for the within-repo
dimension -- so adding a lint kind there automatically extends this
dimension too, no parallel registry to keep in sync.

Each kind's `config_kind` is prefixed "cross_repo_" (e.g.
"cross_repo_eslint") so its rows never collide with the within-repo
dimension's own "eslint"/"ruff"/"golangci" rows in the same
tooling_drift.csv -- both dimensions can report on the same repo without
either being mistaken for the other downstream.
"""
from __future__ import annotations

from pathlib import Path

from .cross_repo_drift import check_cross_repo_lint_drift
from .lint_drift import LINT_KIND_SPECS
from .models import CrossRepoKindSummary, ToolingDriftRow


def run_cross_repo_lint_drift(
    repos: list[Path],
) -> tuple[list[ToolingDriftRow], list[CrossRepoKindSummary]]:
    """Runs once per portfolio (not per-repo): one (rows, summary) result
    per lint kind in `LINT_KIND_SPECS`. `repos` is the full portfolio list
    exactly as passed into `run_tooling_drift` -- de-duplication and the
    single-repo-portfolio skip are `check_cross_repo_lint_drift`'s own
    responsibility, not this function's."""
    all_rows: list[ToolingDriftRow] = []
    summaries: list[CrossRepoKindSummary] = []
    for kind, filename, display_fn in LINT_KIND_SPECS:
        rows, summary = check_cross_repo_lint_drift(repos, f"cross_repo_{kind}", filename, display_fn)
        all_rows.extend(rows)
        summaries.append(summary)
    return all_rows, summaries
