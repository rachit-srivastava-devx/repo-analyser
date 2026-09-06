"""FlagDebtResult: one row per repo in flag_debt.csv. Multi-value fields
(sdk_detected, orphaned_flag_definitions, undefined_flag_references) are
semicolon-joined strings, not lists or sets -- the same CSV-friendly
convention repo_type.RepoTypeResult uses for content_types/signals_matched,
since a plain list would round-trip through csv.DictWriter as Python's
str(list) repr, not a usable value.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FlagDebtResult:
    repo: str
    sdk_detected: str
    flags_referenced_count: int
    flags_defined_count: int
    orphaned_flag_definitions: str
    undefined_flag_references: str
    duplicate_definition_count: int
