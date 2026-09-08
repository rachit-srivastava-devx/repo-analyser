"""Static text-signature SPDX matching -- no network, no license database.

Ordered most-specific-first (mirrors detect_primary_type's "checked in
order, first match wins"): BSD-3-Clause's text is a strict superset of
BSD-2-Clause's two clauses, so BSD-3 must be checked before BSD-2.
Case-sensitive against each license's own canonical casing, which keeps
LGPL-3.0's mixed-case body from satisfying GPL-3.0's all-caps title.

Whitespace in the scanned text and every phrase is normalized (runs
collapsed to one space) so a phrase hard-wrapped across lines matches.

A multi-phrase signature's phrases must be found in declared order
(`_signatures_match_in_order`) -- but order alone doesn't prove two
phrases belong to the *same* fragment. Apache-2.0 and MPL-2.0 both
contain "Version 2.0": a bare, unrelated "the Apache License" mention
followed *anywhere later* by a genuine MPL-2.0 block would satisfy
Apache-2.0's signature purely off MPL's own "Version 2.0". This module
confines phrase order to one structural section (`spdx_sections.py`,
which also explains why a distance bound can't be used instead).
"""
from __future__ import annotations

import re

from .spdx_sections import split_into_sections

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
    """Collapse every run of whitespace -- including a hard-wrap newline --
    to a single space, so a multi-line signature phrase matches regardless
    of where a real LICENSE file happened to wrap it."""
    return _WHITESPACE_RUN.sub(" ", text)


_NORMALIZED_SIGNATURES: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    (spdx_id, tuple(_collapse_whitespace(signature) for signature in signatures))
    for spdx_id, signatures in SPDX_SIGNATURES
)


def _signatures_match_in_order(text: str, signatures: tuple[str, ...]) -> bool:
    """True iff every phrase is found in `text` in order, each starting
    at or after the previous phrase's end -- one forward scan. Callers
    pass one already-section-scoped, collapsed string, so "in order"
    here also means "within the same section" (module docstring)."""
    cursor = 0
    for signature in signatures:
        found_at = text.find(signature, cursor)
        if found_at == -1:
            return False
        cursor = found_at + len(signature)
    return True


def match_spdx_id(text: str) -> str:
    """Return the first SPDX id whose signature is present, in order,
    within one structural section (`spdx_sections.split_into_sections`),
    else "unknown". Never raises -- empty/garbage/huge text simply
    satisfies no signature."""
    sections = [_collapse_whitespace(section) for section in split_into_sections(text)]
    for spdx_id, signatures in _NORMALIZED_SIGNATURES:
        for section in sections:
            if _signatures_match_in_order(section, signatures):
                return spdx_id
    return "unknown"
