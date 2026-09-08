"""Extracts the changed-file list and added-line ranges for a PR's
`merge_base_sha..head_sha` range (see `context.py` for how that range is
resolved).

**The one finding this module exists to get right**: every diff here is
computed FROM `merge_base_sha`, never from `base_sha` directly. A plain
`git diff base_sha..head_sha` (two-dot) diffs two snapshots directly, with
no reference to history -- so it includes every difference between base's
*current* tree and head's, including changes base itself picked up on its
own line of history after the PR forked off it. Those base-only changes
have nothing to do with this PR, but a two-dot diff cannot tell the
difference: it would show them reverting as part of "this PR's diff" simply
because head's tree doesn't have base's later, unrelated edits. Diffing FROM
`merge_base_sha` (the actual fork point) instead gives three-dot semantics
without needing git's `...` syntax (which only works between two refs in a
single invocation, not the merge_base_sha this module already has resolved)
-- it compares head's tree only against the state both branches actually
shared, so only head's own real changes show up. Verified empirically with
a fixture where base and head diverge (see tests/pr_review/conftest.py):
diffing `base..head` directly produced 3 changed files, one of them
(`shared.txt`) entirely a base-only artifact with zero relation to the PR;
diffing `merge_base..head` produced exactly the 1 file the PR actually
touched.

**Design choice -- one combined invocation, not one per changed file**: all
three git calls below (`--name-status`, `--numstat`, `--unified=0`) run
once over the whole range and are parsed (`name_status.py`/`numstat.py`/
`hunks.py`) for every file at once, instead of looping per changed file --
keeps subprocess count at a small constant (3) for a huge PR, and
`--unified=0` strips context lines so parsed size tracks hunk count, not
file contents (only numeric `(start, end)` ranges are ever retained, never
+/- line bodies). See `name_status.py`'s docstring for why `-z` is used.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..core.util import run, write_json
from .assemble import _assemble_changed_files
from .context import PrContext
from .diff_models import ChangedFile
from .flags import _generated_flags
from .hunks import _parse_added_ranges
from .name_status import _parse_name_status_z
from .numstat import _parse_numstat_z


def get_changed_files(repo: Path, ctx: PrContext) -> list[ChangedFile]:
    """Every file touched in `ctx.merge_base_sha..ctx.head_sha` -- diffed
    FROM merge_base, not from ctx.base_sha (see module docstring). An empty
    list is a valid result (e.g. `ctx.commits_in_range == 0`), not an error.
    """
    diff_range = f"{ctx.merge_base_sha}..{ctx.head_sha}"

    name_status_out = run(["git", "diff", "--name-status", "-z", "--find-renames", diff_range],
                           cwd=repo).stdout
    entries = _parse_name_status_z(name_status_out)
    if not entries:
        return []

    numstat_out = run(["git", "diff", "--numstat", "-z", "--find-renames", diff_range], cwd=repo).stdout
    stats = _parse_numstat_z(numstat_out)

    unified_out = run(["git", "diff", "--unified=0", "--find-renames", diff_range], cwd=repo).stdout
    ranges_by_path = _parse_added_ranges(unified_out)

    gen_flags = _generated_flags(repo, ctx.head_sha, [path for _, path, _ in entries])

    return _assemble_changed_files(entries, stats, ranges_by_path, gen_flags)


def run_diff(repo: Path, ctx: PrContext, out_dir: Path) -> Path:
    """Calls `get_changed_files` and persists the result as
    `out_dir/pr_review_diff.json` (mirrors every `collectors/*.py` module's
    `analyze_x` (pure) / `run_x` (writes, returns Path) split)."""
    changed_files = get_changed_files(repo, ctx)
    out_path = out_dir / "pr_review_diff.json"
    write_json(out_path, [asdict(cf) for cf in changed_files])
    return out_path
