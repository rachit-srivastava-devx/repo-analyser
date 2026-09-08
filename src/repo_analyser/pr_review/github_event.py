"""GITHUB_EVENT_PATH JSON fallback -- the second-precedence way to learn a
PR's base/head shas (see `ref_resolution.py`'s `_resolve_base_head` for the
full precedence order this feeds into).

Deliberately NOT `GITHUB_BASE_REF`/`GITHUB_HEAD_REF` -- those are branch
*names*, and a `pull_request`-triggered GitHub Actions job checks out a
synthetic merge commit (`refs/pull/N/merge`) by default, not head's own
branch tip -- `git rev-parse --verify "$GITHUB_HEAD_REF" --` in that
checkout resolves to whatever the runner's local ref with that branch name
happens to point at (frequently wrong or absent entirely), whereas the
event payload's `.head.sha` is the exact commit GitHub computed the PR
against, unambiguously.
"""
from __future__ import annotations

import json
import os


def resolve_from_github_event() -> tuple[str, str] | None:
    """Returns (base_sha, head_sha) read from `GITHUB_EVENT_PATH`'s JSON
    payload when `GITHUB_EVENT_NAME=pull_request` and the event file exists
    and parses with the expected shape. Returns None for every other case
    (not a pull_request event, no event path set, an unreadable/malformed
    file, or JSON missing the expected keys) -- the caller turns a None
    here into one unified, actionable ValueError rather than this module
    raising on partial information.

    Deliberately does not verify the shas name real objects in any repo
    (that is `ref_resolution.py`'s `_verify_ref` job) -- this module's only
    concern is what the event payload said, not whether it is valid.
    """
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        with open(event_path, encoding="utf-8") as f:
            event = json.load(f)
        pr = event["pull_request"]
        return pr["base"]["sha"], pr["head"]["sha"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None  # malformed/missing event file -- fall through to the caller's error
