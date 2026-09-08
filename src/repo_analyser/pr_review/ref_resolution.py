"""Resolves and validates the base/head refs for a single PR review.

Precedence for base/head, in order:

1. Explicit `base`/`head` arguments (both, or neither -- see
   `_resolve_base_head`'s docstring for why "exactly one given" is itself an
   error rather than a partial fallback). Each is validated via
   `git rev-parse --verify <ref> --` before use.
2. When neither is given: `github_event.py`'s `resolve_from_github_event`
   (the `GITHUB_EVENT_PATH` JSON fallback).
3. Neither resolves -> raise `ValueError` naming exactly what's missing.
   Never guess a default (e.g. `HEAD~1`) -- a wrong silent guess here would
   make every downstream module's findings subtly meaningless.

See `merge_base.py` for the separate, independent step of computing the
merge-base once base/head are resolved.
"""
from __future__ import annotations

from pathlib import Path

from ..core.util import run
from .github_event import resolve_from_github_event


def _verify_ref(repo: Path, ref: str) -> str:
    """Resolves `ref` to a full commit SHA, raising `ToolExecutionError` (via
    `core.util.run`'s default `check=True`) if it does not name a real
    object in `repo`. `ref` is attacker-controlled input the moment this
    runs against a fork PR (AGENTS.md §3 rung 8): passed as its own argv
    element, never interpolated into a shell string, and the trailing `--`
    stops a ref crafted to look like a flag (e.g. a branch literally named
    `--upload-pack=...`) from being parsed as one -- verified empirically:
    `git rev-parse --verify -- --evil-flag --` safely reports "Needed a
    single revision" rather than acting on `--evil-flag` as an option.
    """
    return run(["git", "rev-parse", "--verify", ref, "--"], cwd=repo).stdout.strip()


def _resolve_base_head(repo: Path, base: str | None, head: str | None) -> tuple[str, str, str]:
    """Returns (base_sha, head_sha, resolved_via). Precedence steps 1-3 from
    the module docstring; base==head is deliberately NOT special-cased here
    -- it resolves like any other pair (merge_base_sha == that same sha,
    commits_in_range == 0 downstream), which is a valid, non-error PR state
    (e.g. a PR opened before any commits were pushed to it), not a failure.
    """
    if base is not None and head is not None:
        return _verify_ref(repo, base), _verify_ref(repo, head), "explicit"
    if base is not None or head is not None:
        # Deliberately an error, not "use the explicit one and fall back to
        # CI env for the other": silently mixing an explicit override with
        # an unrelated auto-detected value is far more likely to produce a
        # confusing wrong range than to do what the caller intended.
        given, missing = ("base", "head") if base is not None else ("head", "base")
        raise ValueError(
            f"only --{given} was given explicitly; --{missing} must be given too "
            "(or neither, to resolve both from a GitHub Actions pull_request event)"
        )

    event_shas = resolve_from_github_event()
    if event_shas is not None:
        base_sha, head_sha = event_shas
        return _verify_ref(repo, base_sha), _verify_ref(repo, head_sha), "github_event"

    raise ValueError(
        "could not resolve base/head: no explicit base/head given, and "
        "GITHUB_EVENT_NAME=pull_request with a readable GITHUB_EVENT_PATH "
        "(containing pull_request.base.sha / pull_request.head.sha) was not "
        "available either. Pass base/head explicitly, or run this in a "
        "GitHub Actions job triggered by a pull_request event."
    )
