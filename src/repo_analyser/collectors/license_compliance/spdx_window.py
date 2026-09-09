"""Tightest-window span + specificity ranking for match_spdx_id.

Both prior attempts on this bug (ordered-scan, then rule-line sections)
fixed one structural shape of "phrases from two different licenses get
stitched together" and broke on the next. This module replaces both:
for a signature whose phrases are ALL present somewhere in the text (in
declared order -- checked by the caller), compute the minimum-length
window that contains one occurrence of every phrase. A real license's
own phrases sit inside one coherent block and cluster tightly; phrases
borrowed from two unrelated fragments of a mashed-together document are
scattered by construction, so they produce a much wider window. Ranking
every satisfiable signature by this span (smallest wins) picks the
license whose phrases are actually clustered, not whichever license
happens first in declared order.

Complexity: `_find_occurrences` is one `re.finditer` pass per phrase
(linear in text length); `minimum_window_span` is the classic minimum-
window-covering-all-groups two-pointer scan over the merged, sorted
occurrence list -- linear in the number of occurrences, never quadratic
in text length and never re-scanning the whole text per window position.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class _Occurrence:
    start: int
    end: int
    phrase_index: int


def _find_occurrences(text: str, phrases: tuple[str, ...]) -> list[_Occurrence]:
    """Every occurrence of every phrase, tagged with which phrase (by
    declared index, not by string) it is and sorted by start position.
    Indexing by position rather than string content means two phrases
    that happen to share literal text are still tracked as two distinct
    requirements -- not a case in today's SPDX_SIGNATURES, but the
    function stays correct if that ever changes."""
    occurrences = [
        _Occurrence(match.start(), match.end(), index)
        for index, phrase in enumerate(phrases)
        if phrase
        for match in re.finditer(re.escape(phrase), text)
    ]
    occurrences.sort(key=lambda occurrence: occurrence.start)
    return occurrences


def minimum_window_span(text: str, phrases: tuple[str, ...]) -> int | None:
    """Smallest `end - start` of any window in `text` that contains at
    least one occurrence of every phrase in `phrases`, or None if some
    phrase has no occurrence at all. A single-phrase signature's span is
    just that phrase's own length -- there is nothing to cluster against,
    so its "window" is the phrase itself.
    """
    if not phrases:
        return 0
    occurrences = _find_occurrences(text, phrases)
    needed = len(phrases)
    counts = [0] * needed
    satisfied = 0
    left = 0
    best: int | None = None
    for occurrence in occurrences:
        counts[occurrence.phrase_index] += 1
        if counts[occurrence.phrase_index] == 1:
            satisfied += 1
        while satisfied == needed:
            span = occurrence.end - occurrences[left].start
            if best is None or span < best:
                best = span
            counts[occurrences[left].phrase_index] -= 1
            if counts[occurrences[left].phrase_index] == 0:
                satisfied -= 1
            left += 1
    return best


def drop_dominated(
    candidates: list[tuple[int, str, tuple[str, ...], int]],
) -> list[tuple[int, str, tuple[str, ...], int]]:
    """Remove a candidate whose entire phrase set is a strict subset of
    another satisfiable candidate's phrase set.

    Why this exists on top of plain "smallest span wins": BSD-2-Clause's
    two phrases are a literal subset of BSD-3-Clause's three (BSD-3's
    text IS BSD-2's text plus one more clause), so on real BSD-3-Clause
    text, BSD-2-Clause is always trivially satisfiable too -- and its
    2-phrase window is *always* narrower than BSD-3's 3-phrase window,
    since the extra clause can only widen the span. Raw minimum-span
    ranking would therefore misclassify every real BSD-3-Clause file as
    BSD-2-Clause, which is a strictly worse regression than the bug this
    fix targets. A strict phrase-subset relation is the general,
    data-derived signal for "this candidate is a weaker restatement of
    that one, not independent evidence of a different license": drop the
    subset so the superset (more specific, equally satisfiable) is the
    one competing on span with unrelated signatures like Apache-2.0/
    MPL-2.0, which share only one phrase and subset neither.
    """
    phrase_sets = [set(candidate[2]) for candidate in candidates]
    return [
        candidate
        for i, candidate in enumerate(candidates)
        if not any(
            i != j and phrase_sets[i] < phrase_sets[j]
            for j in range(len(candidates))
        )
    ]
