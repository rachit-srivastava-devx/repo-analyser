"""Static text-signature SPDX matching -- no network, no license database.

Two prior attempts fixed "is this signature satisfiable anywhere in the
document" and got the boundary wrong: ordered-scan (ba6e469) let two
unrelated fragments feed one signature as long as they sat in declared
order anywhere in the document; rule-line sections (f0d603c) bounded
that to one delimiter shape and broke on a blank-line/heading-separated
document instead. This version ranks every satisfiable signature by
`spdx_window.minimum_window_span` (tightest cluster of phrases wins) and
`drop_dominated` (a strict phrase-subset of another satisfiable
signature loses, e.g. BSD-2 vs BSD-3) -- see spdx_window.py for the
algorithms, their complexity, and the one documented residual gap.

Declared order (BSD-3 before BSD-2 etc.) is now only the final tie-break
via each candidate's declared index, not the primary selection rule.
Case-sensitive against each license's own canonical casing, which keeps
LGPL-3.0's mixed-case body from satisfying GPL-3.0's all-caps title.
Whitespace in the scanned text and every phrase is collapsed (runs to
one space) so a phrase hard-wrapped across lines still matches.
"""
from __future__ import annotations

import re

from .spdx_window import drop_dominated, minimum_window_span

SPDX_SIGNATURES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LGPL-3.0", ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 3")),
    ("GPL-3.0", ("GNU GENERAL PUBLIC LICENSE", "Version 3")),
    ("GPL-2.0", ("GNU GENERAL PUBLIC LICENSE", "Version 2")),
    ("BSD-3-Clause", (
        "Redistributions of source code must retain the above copyright",
        "Redistributions in binary form must reproduce the above copyright",
        "used to endorse or promote products derived from this software",
    )),
    ("BSD-2-Clause", (
        "Redistributions of source code must retain the above copyright",
        "Redistributions in binary form must reproduce the above copyright",
    )),
    ("Apache-2.0", ("Apache License", "Version 2.0")),
    ("MPL-2.0", ("Mozilla Public License", "Version 2.0")),
    ("ISC", ("Permission to use, copy, modify, and/or distribute this software",)),
    ("MIT", ("Permission is hereby granted, free of charge",)),
    ("Unlicense", ("free and unencumbered software released into the public domain",)),
    ("CC0-1.0", ("Creative Commons Legal Code", "CC0")),
)

_WHITESPACE_RUN = re.compile(r"\s+")


def _collapse_whitespace(text: str) -> str:
    """Collapse whitespace runs (incl. hard-wrap newlines) to one space,
    so a multi-line signature phrase matches regardless of wrap point."""
    return _WHITESPACE_RUN.sub(" ", text)


_NORMALIZED_SIGNATURES: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    (spdx_id, tuple(_collapse_whitespace(signature) for signature in signatures))
    for spdx_id, signatures in SPDX_SIGNATURES
)


def _signatures_match_in_order(text: str, signatures: tuple[str, ...]) -> bool:
    """True iff every phrase is found in `text` in order, each starting
    at or after the previous phrase's end. This is only the
    satisfiability gate (a reversed-clause document never becomes a
    candidate) -- how far apart the phrases are is
    `spdx_window.minimum_window_span`'s job, used only to rank
    signatures this gate already accepted."""
    cursor = 0
    for signature in signatures:
        found_at = text.find(signature, cursor)
        if found_at == -1:
            return False
        cursor = found_at + len(signature)
    return True


def match_spdx_id(text: str) -> str:
    """Return the SPDX id whose signature is present (in declared order)
    with the tightest minimum-window span among all such candidates,
    else "unknown". Never raises -- empty/garbage/huge text simply
    satisfies no signature."""
    normalized_text = _collapse_whitespace(text)
    candidates: list[tuple[int, str, tuple[str, ...], int]] = []
    for declared_index, (spdx_id, signatures) in enumerate(_NORMALIZED_SIGNATURES):
        if not _signatures_match_in_order(normalized_text, signatures):
            continue
        span = minimum_window_span(normalized_text, signatures)
        if span is not None:
            candidates.append((declared_index, spdx_id, signatures, span))

    survivors = drop_dominated(candidates)
    if not survivors:
        return "unknown"
    best = min(survivors, key=lambda candidate: (candidate[3], candidate[0]))
    return best[1]
