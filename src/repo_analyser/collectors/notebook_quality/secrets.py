"""Signal 2: a narrow, LOCAL regex check for obvious secret-shaped
strings in cell source text (AWS-access-key and OpenAI-key shapes only).
This is a cheap, redundant sanity net, NOT this tool's real secret-
scanning mechanism -- security.py's gitleaks pass already scans the
entire tree, including notebooks as plain text, with a real,
comprehensive, actively-maintained rule set. A clean result here means
only "no *obvious* pattern found by these two extra regexes," never "no
secrets in these notebooks" -- defer to security.py's findings for the
real answer."""
from __future__ import annotations

from .cell_text import cell_source_text
from .models import SECRET_PATTERNS


def has_suspected_secret(cell: dict) -> bool:
    text = cell_source_text(cell)
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)
