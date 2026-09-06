"""Static text-signature SPDX matching -- no network, no license database.

Ordered most-specific-first (mirrors detect_primary_type's "checked in
order, first match wins"): BSD-3-Clause's text is a strict superset of
BSD-2-Clause's two redistribution clauses plus an extra endorse/promote
clause, so BSD-3 must be checked before BSD-2 or every BSD-3 file would
also satisfy BSD-2's weaker requirement. Matching is case-sensitive against
each license's own canonical casing, which is also what keeps LGPL-3.0's
body text (which references "version 3 of the GNU General Public License"
in mixed case) from ever satisfying GPL-3.0's all-caps title signature.

Whitespace in both the scanned text and every signature phrase is
normalized (each run of spaces/tabs/newlines collapsed to one space)
before the substring check: real LICENSE files hard-wrap prose at
~70-80 columns, and where that wrap lands is a property of the wrapping
tool, not of the license text itself -- so a phrase written on one line
in the tuple below (e.g. BSD-3-Clause's "Redistributions in binary
form ... the above copyright") commonly appears split across two lines
in the wild. A literal contiguous substring check would then false-
negative a genuine license into "unknown"; collapsing whitespace first
makes the match tolerant of wherever the wrap happened to fall, without
weakening the case-sensitivity above.
"""
from __future__ import annotations

import re

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


def match_spdx_id(text: str) -> str:
    """Return the first SPDX id whose full signature is present in text,
    else "unknown". Never raises -- an empty or garbage text simply
    satisfies no signature.
    """
    normalized_text = _collapse_whitespace(text)
    for spdx_id, signatures in _NORMALIZED_SIGNATURES:
        if all(signature in normalized_text for signature in signatures):
            return spdx_id
    return "unknown"
