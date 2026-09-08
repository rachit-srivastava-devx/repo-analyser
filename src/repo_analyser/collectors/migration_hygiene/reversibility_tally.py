"""Per-convention reversibility tallying, split out of analyze.py to keep
it under the ~80-line convention (AGENTS.md §4). Django, Alembic, and
paired-SQL migrations each classify their own files with a different
per-file `classify_*` function (see reversibility.py/
alembic_reversibility.py), but the fold into a running (reversible,
irreversible, unknown) triple is identical across all three -- one shared
loop here instead of the same three-line accumulate duplicated three times
in analyze_repo.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def tally_reversibility(items: Iterable[T], classify: Callable[[T], str]) -> tuple[int, int, int]:
    """Classifies every item in `items` with `classify` (returning
    "reversible" / "irreversible" / "unknown") and returns the
    (reversible, irreversible, unknown) counts. `items` and `classify`
    are convention-specific -- Django/Alembic pass a Path and
    classify_django/classify_alembic; SQL pairs pass the up-file and a
    closure that resolves its paired down-file before calling
    classify_sql_pair -- this function only does the counting fold, not
    the classification itself.

    Empty `items` returns (0, 0, 0) -- no convention branch in analyze_repo
    calls this unless it already found at least one file of that
    convention, but the function itself makes no such assumption."""
    reversible = irreversible = unknown = 0
    for item in items:
        state = classify(item)
        reversible += state == "reversible"
        irreversible += state == "irreversible"
        unknown += state == "unknown"
    return reversible, irreversible, unknown
