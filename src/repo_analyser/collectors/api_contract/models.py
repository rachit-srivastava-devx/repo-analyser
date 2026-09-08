"""Result dataclass for the api_contract collector. See package docstring
(__init__.py) for the full contract; see patterns.py for the detection
constants used by discovery.py/ci_signals.py/contract_testing.py/
deprecation.py."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiContractResult:
    repo: str
    has_spec: bool
    spec_kinds: str
    spec_file_count: int
    spec_files: str
    spec_parse_errors: str
    has_breaking_change_check: bool
    breaking_change_tools: str
    has_contract_test_tooling: bool
    contract_test_tools: str
    deprecated_with_sunset_count: int
    deprecated_without_sunset_count: int
    skip_reason: str
