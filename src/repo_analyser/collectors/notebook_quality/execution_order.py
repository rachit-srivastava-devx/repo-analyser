"""Signal 3: a CRUDE re-executability PROXY -- whether a notebook's code
cells' `execution_count` values form a strictly increasing sequence in
top-to-bottom order. Consistent with (but does not prove) "this notebook
was run fresh, top to bottom, right before commit" -- the same style of
stated-honestly heuristic as testquality.py's test-pyramid-shape signal.
A non-monotonic sequence is real, unambiguous evidence cells were
executed out of order; a monotonic sequence is compatible with other
benign histories too (e.g. cells reordered after a fresh run), so this
signal can under-flag -- it cannot over-flag a genuine inversion."""
from __future__ import annotations


def execution_counts_in_order(cells: list[dict]) -> list[int]:
    """Real (non-null, integer) `execution_count` values from code
    cells, in the notebook's own top-to-bottom order. A never-run code
    cell has `execution_count: null` (or the key missing entirely) --
    both excluded: no recorded execution is no evidence either way."""
    counts = []
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        ec = cell.get("execution_count")
        if isinstance(ec, int) and not isinstance(ec, bool):
            counts.append(ec)
    return counts


def is_nonlinear_execution(cells: list[dict]) -> bool:
    """True when the executed cells' execution_count values are NOT
    strictly increasing top-to-bottom. Zero or one executed code cells
    are vacuously linear (no adjacent pair to contradict)."""
    counts = execution_counts_in_order(cells)
    # strict=False: the two sides are deliberately different lengths by
    # one (pairing each count with its successor), not a bug to catch.
    return not all(a < b for a, b in zip(counts, counts[1:], strict=False))
