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

A multi-phrase signature's phrases must be found in the SAME relative
order they're declared in SPDX_SIGNATURES, each subsequent phrase
starting at or after the previous phrase's end -- a single left-to-right
scan per signature, not an independent "is this phrase anywhere in the
whole text" check per phrase. The latter (originally `all(p in text for
p in phrases)`) is a real false-positive class, not a hypothetical one:
Apache-2.0's signature is ("Apache License", "Version 2.0") and MPL-2.0's
is ("Mozilla Public License", "Version 2.0") -- both share the literal
phrase "Version 2.0". A NOTICE-style document that mentions the Mozilla
Public License (with its own "Version 2.0") and *separately*, later,
mentions "the Apache License" with no second "Version 2.0" of its own
would satisfy Apache-2.0's two phrases "anywhere, any order" (both are
literally present somewhere in the text) despite never containing real
Apache-2.0 license text -- and since Apache-2.0 is checked before MPL-2.0
below, it would win the false match. Requiring ordered, forward-only
matching closes that: Apache-2.0's "Version 2.0" phrase must appear at
or after its "Apache License" phrase, which the MPL-only text does not
satisfy.
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


def _signatures_match_in_order(text: str, signatures: tuple[str, ...]) -> bool:
    """True iff every phrase in `signatures` is found in `text`, each
    subsequent phrase starting at or after the previous phrase's end --
    a single forward scan through `text`, not an independent whole-text
    search per phrase. This is what makes a multi-phrase signature mean
    "this text contains these clauses in this relative order" (the real
    structure of a license document) rather than "these phrases are each
    present somewhere, in any order, at any distance" (satisfiable by
    unrelated text that happens to quote fragments of two different
    licenses -- see the Apache-2.0/MPL-2.0 "Version 2.0" case in this
    module's docstring).
    """
    cursor = 0
    for signature in signatures:
        found_at = text.find(signature, cursor)
        if found_at == -1:
            return False
        cursor = found_at + len(signature)
    return True


def match_spdx_id(text: str) -> str:
    """Return the first SPDX id whose full signature is present in text,
    with its phrases in declared order, else "unknown". Never raises --
    an empty or garbage text simply satisfies no signature.
    """
    normalized_text = _collapse_whitespace(text)
    for spdx_id, signatures in _NORMALIZED_SIGNATURES:
        if _signatures_match_in_order(normalized_text, signatures):
            return spdx_id
    return "unknown"
