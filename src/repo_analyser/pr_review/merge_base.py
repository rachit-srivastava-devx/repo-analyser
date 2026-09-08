"""Computes the merge-base between an already-resolved base/head sha pair.

`merge_base_sha` is resolved exactly once per PR review (see `context.py`'s
`resolve_pr_context`), becoming the range every downstream module diffs
FROM -- see `diff.py`'s module docstring for why merge_base, not base, is
the correct starting point for a PR diff.
"""
from __future__ import annotations

from pathlib import Path

from ..core.util import RunResult, ToolExecutionError, run


def _merge_base(repo: Path, base_sha: str, head_sha: str) -> str:
    """`git merge-base base_sha head_sha`, with a real, actionable error on
    failure instead of a bare (often EMPTY -- verified empirically: this
    fails with returncode 1 and both stdout AND stderr blank) git stderr
    dump. A shallow clone (`git fetch --depth=1`, GitHub Actions'
    checkout@v4 default) is by far the most common real-world cause: base
    and head each resolve to a real object, but neither's fetched history
    reaches far enough back to share a visible common ancestor.
    """
    result: RunResult = run(["git", "merge-base", base_sha, head_sha], cwd=repo, check=False)
    if result.returncode == 0:
        return result.stdout.strip()

    shallow = run(["git", "rev-parse", "--is-shallow-repository"], cwd=repo, check=False)
    if shallow.returncode == 0 and shallow.stdout.strip() == "true":
        likely_cause = (
            "this repo IS a shallow clone -- almost certainly the cause. Fix: set "
            "`fetch-depth: 0` (full history) on the checkout step in the calling CI config."
        )
    else:
        likely_cause = (
            "this repo does not report itself as shallow, so base and head may "
            "genuinely share no history (e.g. force-pushed/rewritten refs, or "
            "base/head from unrelated repos). If this runs in CI, double-check "
            "`fetch-depth: 0` is set on the checkout step regardless -- that is "
            "still the most common real-world cause even when this signal is "
            "inconclusive."
        )
    raise ToolExecutionError(
        result.cmd, result.returncode,
        f"git merge-base found no common ancestor between {base_sha} and {head_sha}: {likely_cause} "
        f"(original git stderr: {result.stderr.strip() or '<empty>'})",
    )
