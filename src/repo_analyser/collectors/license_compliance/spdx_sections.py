"""Split raw license/NOTICE text into structurally-delimited sections.

`match_spdx_id` requires a signature's phrases to be found together
within one section, not merely in order anywhere in the whole document.
Order alone doesn't establish that two phrases belong to the same license
fragment -- see spdx_match.py's module docstring for the concrete
Apache-2.0/MPL-2.0 "Version 2.0" false positive this closes.

A fixed character-distance window between phrases cannot serve as that
bound instead: a legitimate same-license gap can be *longer* than an
illegitimate cross-license one. Concretely, BSD-3-Clause's own
blank-line-separated numbered clauses 2 and 3 are ~220 characters apart
in a real hard-wrapped LICENSE file, while the Apache/MPL false positive
needs only ~75 characters of connective NOTICE prose between the bare
"Apache License" mention and the unrelated MPL block's "Version 2.0" --
any single threshold that tolerates the former also admits the latter.

Instead, a line that is itself a horizontal rule (3+ repeats of one of
-, =, *, _, ~ -- the conventional NOTICE/THIRD-PARTY-NOTICES/Markdown
section-break characters) is treated as a hard section boundary. Plain
blank lines are deliberately NOT a boundary: real LICENSE templates (the
standard BSD-3-Clause text included) put a blank line between each
numbered clause, and splitting there would scatter one license's own
signature across sections and misclassify it as "unknown".

Residual risk: a document that mixes fragments of two different licenses
with no rule line and no other structural marker between them is not
caught by this -- only whole-document proximity would, and this module's
own docstring above shows that can't be bounded safely either.
"""
from __future__ import annotations

import re

_RULE_LINE = re.compile(r"^[ \t]*([-=*_~])\1{2,}[ \t]*$\r?\n?", re.MULTILINE)


def split_into_sections(text: str) -> list[str]:
    """Split `text` on horizontal-rule lines; the rule lines themselves
    are dropped. Returns `[text]` unchanged when no rule line is present,
    so a single-block LICENSE file behaves exactly as before this module
    existed. Never raises on empty, malformed, or huge input -- a single
    linear scan via `re.finditer`, no backtracking blowup risk."""
    sections: list[str] = []
    cursor = 0
    for match in _RULE_LINE.finditer(text):
        sections.append(text[cursor : match.start()])
        cursor = match.end()
    sections.append(text[cursor:])
    return sections
