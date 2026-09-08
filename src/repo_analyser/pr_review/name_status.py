"""Parses `git diff --name-status -z` output into (status, path, old_path)
triples.

**Why `-z`**: plain-text output abbreviates a rename's path with git's own
`{old => new}` notation, which factors out a common prefix/suffix and is
genuinely ambiguous to reverse for a path that itself contains the literal
substring " => ". `-z` NUL-delimits records and, for a rename, emits old
and new paths as two separate, unabbreviated NUL-terminated fields --
verified empirically (see this module's tests) against a rename nested
under a shared directory prefix, which is exactly the case the plain-text
form abbreviates. `numstat.py`'s `_parse_numstat_z` reads the same `-z`
convention for the same reason.
"""
from __future__ import annotations


def _drop_trailing_empty(tokens: list[str]) -> list[str]:
    """`"a\\0b\\0".split("\\0")` yields a trailing "" for the terminating
    NUL -- drop exactly that one artifact, nothing else."""
    if tokens and tokens[-1] == "":
        tokens.pop()
    return tokens


def _parse_name_status_z(text: str) -> list[tuple[str, str, str | None]]:
    """`git diff --name-status -z` output -> `[(status, path, old_path)]`,
    in git's own output order. `old_path` is None except for a rename."""
    tokens = _drop_trailing_empty(text.split("\0"))
    entries: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if status[:1] == "R":  # e.g. "R100"; --find-copies not passed, so never "C"
            old_path, new_path = tokens[i + 1], tokens[i + 2]
            entries.append((status[:1], new_path, old_path))
            i += 3
        else:
            entries.append((status, tokens[i + 1], None))
            i += 2
    return entries
