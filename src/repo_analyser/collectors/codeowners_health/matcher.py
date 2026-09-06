"""Last-match-wins CODEOWNERS pattern matching -- the same semantics as
.gitignore (https://git-scm.com/docs/gitignore#_pattern_format), applied
to a single CODEOWNERS pattern column: trailing `/` restricts a match to
files strictly inside that directory (at any depth); leading `/` anchors
the match to position 0 (repo root); otherwise the pattern matches at any
depth. Segment-based matching via fnmatch.fnmatchcase (not fnmatch.fnmatch,
which case-normalizes on Windows -- this must match identically regardless
of the host OS this collector runs on).
"""
from __future__ import annotations

from fnmatch import fnmatchcase

from .parser import CodeownersRule


def pattern_matches(pattern: str, file_path: str) -> bool:
    anchored = pattern.startswith("/")
    dir_only = pattern.endswith("/")
    pattern_parts = pattern.strip("/").split("/")
    file_parts = file_path.split("/")
    width = len(pattern_parts)

    offsets = [0] if anchored else range(len(file_parts) - width + 1)
    for offset in offsets:
        if offset + width > len(file_parts):
            continue  # pattern is wider than what's left of the path (only reachable when anchored)
        if dir_only and offset + width >= len(file_parts):
            continue  # the file must be strictly inside the matched directory
        window = file_parts[offset:offset + width]
        # strict=True: the guard above already ensures window has exactly
        # `width` elements, i.e. len(window) == len(pattern_parts) always.
        if all(fnmatchcase(part, seg) for part, seg in zip(window, pattern_parts, strict=True)):
            return True
    return False


def match_all(
    rules: list[CodeownersRule], files: list[str]
) -> tuple[dict[str, tuple[str, ...]], set[int]]:
    """Returns (ownership, matched_rule_indices). `ownership` maps each
    file to the owners of the LAST rule that matched it (gitignore
    semantics: a later line overrides an earlier one for any file both
    apply to). `matched_rule_indices` holds the index of every rule that
    matched at least one file, regardless of whether it ultimately won --
    used to compute stale_rule_count (the rules NOT in this set)."""
    ownership: dict[str, tuple[str, ...]] = {}
    matched_rule_indices: set[int] = set()
    for file_path in files:
        for index, rule in enumerate(rules):
            if pattern_matches(rule.pattern, file_path):
                ownership[file_path] = rule.owners
                matched_rule_indices.add(index)
    return ownership, matched_rule_indices
