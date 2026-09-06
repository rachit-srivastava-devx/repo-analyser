"""Static text-signature SPDX matching -- no network, no license database.

Ordered most-specific-first (mirrors detect_primary_type's "checked in
order, first match wins"): BSD-3-Clause's text is a strict superset of
BSD-2-Clause's two redistribution clauses plus an extra endorse/promote
clause, so BSD-3 must be checked before BSD-2 or every BSD-3 file would
also satisfy BSD-2's weaker requirement. Matching is case-sensitive against
each license's own canonical casing, which is also what keeps LGPL-3.0's
body text (which references "version 3 of the GNU General Public License"
in mixed case) from ever satisfying GPL-3.0's all-caps title signature.
"""
from __future__ import annotations

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


def match_spdx_id(text: str) -> str:
    """Return the first SPDX id whose full signature is present in text,
    else "unknown". Never raises -- an empty or garbage text simply
    satisfies no signature.
    """
    for spdx_id, signatures in SPDX_SIGNATURES:
        if all(signature in text for signature in signatures):
            return spdx_id
    return "unknown"
