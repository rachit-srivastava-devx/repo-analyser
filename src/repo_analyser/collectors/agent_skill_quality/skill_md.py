"""Signal: SKILL.md frontmatter quality.

A `SKILL.md` file IS one tool definition. Its YAML frontmatter (between
`---` delimiters) is expected to carry a `name` and a `description` key --
verified against a real example on this machine
(`~/.claude/skills/content-research-writer/SKILL.md`) rather than
guessed, per AGENTS.md's rule against inventing a schema.

`name` AND `description` keys must both be present for a valid schema --
Claude Code's own convention requires both (confirmed against the real
example above).
"""
from __future__ import annotations

from pathlib import Path

import yaml


def _grade_skill_md(path: Path) -> tuple[int, int, int]:
    """One SKILL.md file = one tool definition. Returns (found,
    valid_schema, with_description) deltas -- found is always 1 for a file
    that exists at all; the other two are 0 when the frontmatter block is
    missing, never closes, or fails to parse as YAML. A malformed file
    counts as "found but not valid schema," the same non-crashing outcome
    repo_type.py's own `_read_json` establishes for a malformed
    package.json -- never a crash of the whole collector run over one bad
    file."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return 1, 0, 0
    if not text.startswith("---"):
        return 1, 0, 0
    end = text.find("\n---", 3)
    if end == -1:  # opening delimiter present, closing one never arrives
        return 1, 0, 0
    try:
        frontmatter = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return 1, 0, 0
    if not isinstance(frontmatter, dict):
        return 1, 0, 0
    valid = 1 if ("name" in frontmatter and "description" in frontmatter) else 0
    description = frontmatter.get("description")
    with_description = 1 if isinstance(description, str) and description.strip() else 0
    return 1, valid, with_description
