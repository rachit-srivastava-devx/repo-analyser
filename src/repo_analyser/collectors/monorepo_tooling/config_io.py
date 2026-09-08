"""Safe text reading shared by the nx/turbo/pants signal modules -- same
shape as api_contract/text_io.py, duplicated rather than imported because
AGENTS.md SS4 forbids one collector's production code from importing
another collector's internal modules."""
from __future__ import annotations

from pathlib import Path


def read_text_safe(path: Path) -> tuple[str | None, str | None]:
    """Returns (text, error). error is set (and text is None) only for a
    file that exists but can't be read as UTF-8 -- a real, distinct-from-
    zero-found failure mode. A zero-byte file is not an error: it reads as
    ("", None), and each signal module decides what an empty config means
    for its own tool (e.g. empty JSON text fails to parse; an empty TOML
    file is syntactically valid TOML with no tables)."""
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"{path}: not valid UTF-8 ({e})"
    except OSError as e:
        return None, f"{path}: unreadable ({e})"
