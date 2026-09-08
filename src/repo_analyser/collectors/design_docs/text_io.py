"""Safe text reading shared across this package. Every doc/ADR/runbook file
read here is user-controlled content from a target repo (AGENTS.md §3's
"untrusted input" rung) -- nothing here executes or evals it, only reads
and regex-scans the text."""
from __future__ import annotations

from pathlib import Path


def read_text_safe(path: Path) -> tuple[str | None, str | None]:
    """Returns (text, error). error is set (and text is None) for a file
    that exists but can't be decoded as UTF-8 -- a real, distinct-from-
    zero-found failure mode (the "unicode content" edge case is the
    *success* path here; genuinely undecodable bytes are the failure
    path, reported as adr_malformed_count rather than crashing the
    collector run)."""
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"{path}: not valid UTF-8 ({e})"
    except OSError as e:
        return None, f"{path}: unreadable ({e})"


def join_sample(items: list[str], cap: int) -> str:
    """";"-joined sample, capped at `cap` entries with a "+N more" suffix
    when truncated -- same shape as migration_hygiene's join_sample. The
    caller always reports the true count in a separate *_count field; this
    string is a preview, never the source of truth for "how many"."""
    if len(items) <= cap:
        return ";".join(items)
    shown = items[:cap]
    return ";".join(shown) + f";+{len(items) - cap} more"
