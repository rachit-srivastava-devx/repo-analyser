"""Locate and parse a CODEOWNERS file, using GitHub's own precedence order
and line syntax: a `<pattern> <owner1> [owner2 ...]` line per rule, blank
lines and full-line `#` comments skipped, inline `#` comments stripped.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_CANDIDATE_PATHS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")


@dataclass(frozen=True)
class CodeownersRule:
    pattern: str
    owners: tuple[str, ...]
    line_number: int


def find_codeowners(repo: Path) -> Path | None:
    """First existing candidate wins, in GitHub's real precedence order:
    .github/CODEOWNERS, then root CODEOWNERS, then docs/CODEOWNERS. A
    plain disk check, independent of git tracking status -- an untracked
    (not yet `git add`ed) CODEOWNERS file is still the one GitHub itself
    would use."""
    for candidate in _CANDIDATE_PATHS:
        path = repo / candidate
        if path.is_file():
            return path
    return None


def parse_codeowners(path: Path) -> list[CodeownersRule]:
    """A line with a pattern but no owners is malformed and is skipped,
    not a crash. Duplicate identical pattern lines are kept as separate
    rules -- each is a distinct line, and `stale_rule_count` counts them
    independently rather than deduplicating by pattern text."""
    rules: list[CodeownersRule] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        pattern, owners = tokens[0], tuple(tokens[1:])
        if not owners:
            continue
        rules.append(CodeownersRule(pattern=pattern, owners=owners, line_number=line_number))
    return rules
