"""Data shape and constants shared across doc_quality's submodules."""
from __future__ import annotations

import re
from dataclasses import dataclass

# interrogate's own default-verbosity summary line, e.g.:
#   RESULT: PASSED (minimum: 0.0%, actual: 62.5%)
INTERROGATE_RESULT_RE = re.compile(r"RESULT:\s+\w+\s+\(minimum:\s*[\d.]+%,\s*actual:\s*([\d.]+)%\)")
INTERROGATE_NO_FILES_MARKER = "No Python or Python-like files found"

# Reused, not reinvented: same eslint config filenames lint_quality.py's
# _eslint() already checks for a project's own config. Duplicated locally
# rather than imported -- lint_quality.py isn't in this task's scope, and
# docs/ROADMAP.md sets this exact precedent for a sibling collector
# (api_contract.py duplicating performance.py's small helpers rather than
# reaching into that file).
ESLINT_CONFIG_FILENAMES = (
    "eslint.config.js", "eslint.config.mjs", "eslint.config.ts",
    ".eslintrc.js", ".eslintrc.json",
)
JSDOC_REF_RE = re.compile(r"\bjsdoc\b", re.IGNORECASE)

CHANGELOG_FILENAMES = {"changelog.md", "history.md"}
CHANGELOG_HEADING_RE = re.compile(r"^#{1,4}\s+(.*)$", re.MULTILINE)
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class DocQualityResult:
    repo: str
    doc_comment_coverage_pct: float
    doc_comment_tool: str
    has_changelog: bool
    changelog_last_entry_date: str
    changelog_stale_vs_latest_tag: str
    skip_reason: str = ""
