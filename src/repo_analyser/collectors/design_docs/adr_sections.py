"""ADR content signals that need no git history: context/decision/
consequences-shaped sections, and the reversibility tag. Both are pure text
scans of one ADR file's content -- degrade gracefully on any text (an ADR
using neither heading nor bold-field convention just reports False, not an
error; this is a heuristic on *shape*, stated plainly, same spirit as
api_contract's/doc_quality's own regex-based signals)."""
from __future__ import annotations

from .models import ADR_REVERSIBILITY_TAG_RE, ADR_SECTION_PATTERNS


def has_standard_sections(text: str) -> bool:
    """True only when all three of context/decision/consequences are
    present -- a partial match (e.g. "Decision" and "Consequences" but no
    "Context") does not count as "has the standard shape"; the CSV's
    section-count columns (computed by the caller across all ADRs) are
    where a partial-adoption signal would show up in aggregate, not here."""
    return all(pattern.search(text) for pattern in ADR_SECTION_PATTERNS.values())


def is_reversibility_tagged(text: str) -> bool:
    """Whether this ADR carries an explicit one-way-door/two-way-door/
    reversible/irreversible tag anywhere in its text. Word-boundary,
    case-insensitive -- see models.ADR_REVERSIBILITY_TAG_RE's docstring for
    why "reversible" never accidentally matches inside "irreversible"."""
    return bool(ADR_REVERSIBILITY_TAG_RE.search(text))
