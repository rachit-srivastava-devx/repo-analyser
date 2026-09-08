"""Per-repo orchestration: combines the three quality signals over every
notebook found, and counts what couldn't be parsed at all.

An unparseable notebook is never folded into "0 notebooks" -- it still
counts toward `notebooks_total` (the file genuinely exists and is a
notebook-shaped artifact) and is additionally counted in
`notebooks_unparseable`, so "no notebooks here" and "notebooks here we
couldn't read" are never confused. The three quality signals are
evaluated ONLY over notebooks that parsed -- asserting a signal with zero
evidence would itself be a silently-wrong result (AGENTS.md SS3)."""
from __future__ import annotations

from pathlib import Path

from .discovery import find_notebooks, read_notebook
from .execution_order import is_nonlinear_execution
from .models import NotebookQualityResult
from .outputs import has_uncleared_outputs
from .secrets import has_suspected_secret


def _analyze_notebook(nb: dict) -> tuple[bool, bool, bool]:
    """Returns (has_uncleared_outputs, has_suspected_secret,
    is_nonlinear_execution) for one already-parsed notebook. Non-dict
    entries inside `cells` (confirmed to be a list by read_notebook, but
    not necessarily a list *of dicts*) are skipped rather than raising."""
    cells = [c for c in nb.get("cells", []) if isinstance(c, dict)]
    uncleared = any(has_uncleared_outputs(c) for c in cells)
    secret = any(has_suspected_secret(c) for c in cells)
    nonlinear = is_nonlinear_execution(cells)
    return uncleared, secret, nonlinear


def analyze_repo(repo: Path) -> NotebookQualityResult:
    notebook_paths = find_notebooks(repo)
    if not notebook_paths:
        return NotebookQualityResult(
            repo=repo.name, notebooks_total=0, notebooks_with_uncleared_outputs=0,
            notebooks_with_suspected_secrets=0, notebooks_nonlinear_execution=0,
            notebooks_unparseable=0, skip_reason="no .ipynb files found",
        )

    uncleared_count = 0
    secret_count = 0
    nonlinear_count = 0
    unparseable_count = 0
    for path in notebook_paths:
        parsed = read_notebook(path)
        if parsed is None:
            unparseable_count += 1
            continue
        uncleared, secret, nonlinear = _analyze_notebook(parsed)
        uncleared_count += int(uncleared)
        secret_count += int(secret)
        nonlinear_count += int(nonlinear)

    return NotebookQualityResult(
        repo=repo.name,
        notebooks_total=len(notebook_paths),
        notebooks_with_uncleared_outputs=uncleared_count,
        notebooks_with_suspected_secrets=secret_count,
        notebooks_nonlinear_execution=nonlinear_count,
        notebooks_unparseable=unparseable_count,
        skip_reason="",
    )
