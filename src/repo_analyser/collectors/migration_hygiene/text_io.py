"""Safe text/binary reading shared across this package. Every migration/
schema file this collector reads is user-controlled content (a target
repo's own files -- AGENTS.md §3's "untrusted input" rung), so nothing
here ever executes or evals it; only regex/AST-parses the bytes/text."""
from __future__ import annotations

from pathlib import Path


def read_text_safe(path: Path) -> tuple[str | None, str | None]:
    """Returns (text, error). error is set (and text is None) for a file
    that exists but can't be decoded as UTF-8 -- a real, distinct-from-
    zero-found failure mode. The "unicode in migration content" edge case
    is the *success* path here; genuinely undecodable bytes are the
    failure path."""
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"{path}: not valid UTF-8 ({e})"
    except OSError as e:
        return None, f"{path}: unreadable ({e})"


def join_sample(items: list[str], cap: int) -> str:
    """";"-joined sample, capped at `cap` entries with a "+N more" suffix
    when truncated. The caller always reports the true count separately
    -- this string is a preview, never the source of truth for "how
    many"."""
    if len(items) <= cap:
        return ";".join(items)
    shown = items[:cap]
    return ";".join(shown) + f";+{len(items) - cap} more"
