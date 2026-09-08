"""Data shape and detection constants for the design_docs collector. See
package docstring (__init__.py) for the full contract."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Fixed, conventional candidate paths -- matches api_contract's/ci_gates.py's
# own "conventional paths, not a blind glob" precedent. All five are checked
# and every one found is reported (docs/ARCHITECTURE.md's "report all
# candidates, don't silently pick one" instruction for this collector).
#
# Known, documented filesystem caveat: "docs/ARCHITECTURE.md" and
# "docs/architecture.md" differ only by case. On a case-insensitive
# filesystem (macOS's and Windows's default), a repo with just one such
# file will have BOTH candidates resolve to it and BOTH get reported in
# hld_docs_found -- not two real files, one filesystem entry counted
# twice. On a case-sensitive filesystem (most CI Linux runners) they are
# genuinely distinct. This collector does not special-case around it: it
# is inherent to running the same fixed candidate list is_file() check
# across platforms with different case-folding, not a bug in the check
# itself, and is called out here rather than silently producing a
# platform-dependent count with no explanation.
HLD_CANDIDATES = [
    "docs/ARCHITECTURE.md", "ARCHITECTURE.md", "docs/architecture.md",
    "docs/design.md", "docs/HLD.md",
]

ADR_DIR_CANDIDATES = ["docs/adr", "docs/decisions", "adr"]
# This repo's own docs/adr/NNNN-*.md convention, and generic MADR-style
# NNNN-title.md -- the same shape, so one regex covers both.
ADR_FILENAME_RE = re.compile(r"^\d{4}-.+\.md$", re.IGNORECASE)

RUNBOOK_FILE_CANDIDATES = ["RUNBOOK.md", "docs/runbook.md", "docs/operations.md", "docs/on-call.md"]
README_SECTION_RE = re.compile(r"^#{1,4}\s*(runbook|rollback|on-call|oncall)\b", re.IGNORECASE | re.MULTILINE)

# Lightweight keyword-presence signal, not semantic understanding (task
# scope). Four independent categories; a runbook can hit any subset.
RUNBOOK_KEYWORD_PATTERNS = {
    "deploy": re.compile(r"\bdeploy(ment)?\b", re.IGNORECASE),
    "rollback": re.compile(r"\brollback\b", re.IGNORECASE),
    "on_call": re.compile(r"\bon[- ]?call\b", re.IGNORECASE),
    "known_failure_mode": re.compile(r"\bknown[- ]?(issue|failure)s?\b|\bfailure\s+modes?\b", re.IGNORECASE),
}

# ADR context/decision/consequences-shaped section detection: an ATX heading
# or a bold field label, either convention counts (MADR templates use both).
ADR_SECTION_PATTERNS = {
    "context": re.compile(r"^#{1,4}\s*context\b|\*\*context\*\*\s*:?", re.IGNORECASE | re.MULTILINE),
    "decision": re.compile(r"^#{1,4}\s*decision\b|\*\*decision\*\*\s*:?", re.IGNORECASE | re.MULTILINE),
    "consequences": re.compile(r"^#{1,4}\s*consequences\b|\*\*consequences\*\*\s*:?", re.IGNORECASE | re.MULTILINE),
}

# "Status" label (heading or bold field), searched for a value word in a
# small window after it -- same windowed-search shape as api_contract's own
# SUNSET_SIGNAL_RE precedent, reused here for the same reason: a template's
# label and its value are often on separate lines.
ADR_STATUS_LABEL_RE = re.compile(
    r"^#{1,4}\s*status\s*$|\*\*status:?\*\*\s*:?|^status\s*:", re.IGNORECASE | re.MULTILINE
)
ADR_STATUS_VALUES = ("accepted", "proposed", "rejected", "deprecated", "superseded")
ADR_STATUS_WINDOW_LINES = 3

# Case-insensitive, word-boundary tag search. "irreversible" and
# "reversible" never cross-match each other: \b requires a non-word/word
# transition, and there is none between the "ir" prefix and "reversible".
ADR_REVERSIBILITY_TAG_RE = re.compile(
    r"\bone[- ]way[- ]door\b|\btwo[- ]way[- ]door\b|\birreversible\b|\breversible\b",
    re.IGNORECASE,
)

SAMPLE_CAP = 25


@dataclass
class DesignDocsResult:
    repo: str
    # HLD presence & freshness
    has_hld: bool
    hld_docs_found: str
    hld_untracked_count: int
    hld_days_since_doc_touched: int | None
    hld_days_since_repo_last_commit: int | None
    repo_has_commits: bool
    # ADR discovery + section discipline
    has_adr_dir: bool
    adr_dirs_found: str
    adr_file_count: int
    adr_files_sample: str
    adr_malformed_count: int
    adr_with_standard_sections_count: int
    # ADR status + "immutable once accepted" signal
    adr_status_accepted_count: int
    adr_status_unknown_count: int
    adr_modified_after_acceptance_count: int
    adr_acceptance_history_unknown_count: int
    # Decision reversibility tagging
    adr_reversibility_tagged_count: int
    # Runbook / operational-doc coverage
    has_runbook: bool
    runbook_docs_found: str
    runbook_keyword_categories_found: str
    runbook_keyword_category_count: int
    skip_reason: str
