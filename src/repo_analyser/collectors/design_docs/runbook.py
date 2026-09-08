"""Runbook/operational-doc coverage: a dedicated file (models.
RUNBOOK_FILE_CANDIDATES), or a Runbook/Rollback/On-call-shaped section
inside README.md. Either counts as "has a runbook" -- a small team
documenting operations inline in the README is a legitimate, common
choice, not a lesser one this collector should penalize by ignoring it.

The keyword-presence signal is scanned across whatever runbook-ish text
was actually found (the dedicated file's full text, or the whole README's
text when only a README section header matched -- the header found the
section exists; the keyword scan then runs on the whole file rather than
trying to slice out just that section, since Markdown section boundaries
are themselves a heuristic this module doesn't need two of)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import README_SECTION_RE, RUNBOOK_FILE_CANDIDATES, RUNBOOK_KEYWORD_PATTERNS
from .text_io import read_text_safe


@dataclass
class RunbookSignal:
    has_runbook: bool
    docs_found: list[str]
    keyword_categories: list[str]


def collect_runbook_signal(repo: Path) -> RunbookSignal:
    docs_found: list[str] = []
    texts: list[str] = []

    for rel in RUNBOOK_FILE_CANDIDATES:
        p = repo / rel
        if p.is_file():
            docs_found.append(rel)
            text, _err = read_text_safe(p)
            if text is not None:
                texts.append(text)

    readme = repo / "README.md"
    if readme.is_file():
        text, _err = read_text_safe(readme)
        if text is not None and README_SECTION_RE.search(text):
            docs_found.append("README.md#runbook-section")
            texts.append(text)

    combined = "\n".join(texts)
    categories = sorted(name for name, pattern in RUNBOOK_KEYWORD_PATTERNS.items() if pattern.search(combined))
    return RunbookSignal(
        has_runbook=bool(docs_found),
        docs_found=sorted(set(docs_found)),
        keyword_categories=categories,
    )
