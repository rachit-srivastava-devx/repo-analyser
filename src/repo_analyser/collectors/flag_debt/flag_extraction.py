"""Regex-based extraction of flag *references*: calls to a known in-house
gate function (`is_enabled`, `feature_enabled`, `isFeatureEnabled` -- exact,
case-sensitive names, per the brief) whose first argument is a string
literal, plus a source-level `FEATURE_FLAGS = {...}` / `const flags = {...}`
dict literal, one of the two places a flag *definition* can live (the other
is a root config file -- see flag_definitions.py).

Both scans work on a file's whole text (not line-by-line), so a call or a
dict literal that wraps across lines is still found; neither attempts real
expression evaluation -- a variable first argument, or a value that isn't a
plain quoted string, is simply not matched, not guessed at.
"""
from __future__ import annotations

import re

FLAG_CALL_RE = re.compile(
    r'\b(?:is_enabled|feature_enabled|isFeatureEnabled)\s*\(\s*(?P<q>[\'"])(?P<flag>[^\'"]*)(?P=q)'
)

DEFINITION_DICT_RE = re.compile(
    r'^\s*FEATURE_FLAGS\s*=\s*\{'
    r'|^\s*(?:export\s+)?(?:const|let|var)\s+flags\s*=\s*\{',
    re.MULTILINE,
)


def extract_flag_references(text: str) -> set[str]:
    return {m.group("flag") for m in FLAG_CALL_RE.finditer(text) if m.group("flag")}


def _scan_object_keys(text: str, start: int) -> list[str]:
    """Walks the `{...}` beginning right after `start` (start is the index
    just past the opening brace matched by DEFINITION_DICT_RE), tracking
    brace depth and skipping over string contents (honoring backslash
    escapes), so a `"key":` pair is only collected at depth == 1 -- a
    nested per-item metadata object (e.g. {"beta": {"enabled": true}})
    correctly yields only "beta". Tolerates a missing closing brace
    (truncated file) by stopping at end of text instead of raising.
    """
    keys: list[str] = []
    depth = 1
    i, n = start, len(text)
    while i < n and depth > 0:
        ch = text[i]
        if ch in "\"'":
            quote, j = ch, i + 1
            while j < n and text[j] != quote:
                j += 2 if text[j] == "\\" else 1
            token = text[i + 1:j]
            k = j + 1
            while k < n and text[k] in " \t\r\n":
                k += 1
            if depth == 1 and k < n and text[k] == ":":
                keys.append(token)
            i = j + 1
            continue
        depth += 1 if ch == "{" else -1 if ch == "}" else 0
        i += 1
    return keys


def extract_dict_literal_definitions(text: str) -> list[str]:
    keys: list[str] = []
    for m in DEFINITION_DICT_RE.finditer(text):
        keys.extend(_scan_object_keys(text, m.end()))
    return keys
