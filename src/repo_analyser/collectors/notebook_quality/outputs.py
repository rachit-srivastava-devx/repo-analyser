"""Signal 1: outputs cleared before commit. A real leak vector -- notebook
outputs can embed printed secrets or data samples, or just bloat git
history with binary image blobs that shouldn't be there."""
from __future__ import annotations


def has_uncleared_outputs(cell: dict) -> bool:
    if cell.get("cell_type") != "code":
        return False
    outputs = cell.get("outputs")
    # A code cell with no `outputs` key at all (rather than an empty
    # list) is treated the same as an empty list: there is no recorded
    # output to flag as uncleared either way.
    return isinstance(outputs, list) and len(outputs) > 0
