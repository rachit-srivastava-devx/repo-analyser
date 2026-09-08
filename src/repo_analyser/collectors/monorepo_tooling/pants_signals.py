"""Signal 4: Pants (pants.toml). No TOML-parser dependency -- matches
collectors/repo_type/fileio.py's read_toml_has_table precedent (this
codebase's py3.10 floor predates stdlib tomllib, and this repo has already
deliberately chosen not to add a TOML-parser dependency for a
presence/shape check that doesn't need one; see
collectors/license_compliance/manifest_toml_licenses.py's docstring for
the same call made the same way).

"Valid TOML" here is a bounded structural proxy, not full grammar
validation: the file must contain at least one top-level `[section]`
header or a `key = value` line. A genuinely malformed pants.toml that still
happens to contain a bare "[GLOBAL]"-shaped line reads as valid here --
the same class of limitation read_toml_has_table already accepts. Real
grammar validation would need a TOML parser this codebase doesn't
otherwise carry."""
from __future__ import annotations

import re
from pathlib import Path

from .config_io import read_text_safe
from .patterns import PANTS_CONFIG_FILENAME

_SECTION_RE = re.compile(r"(?m)^\[([A-Za-z0-9_.\-]+)\]\s*$")
_KV_RE = re.compile(r"(?m)^\s*[A-Za-z0-9_.\-]+\s*=")
BACKEND_SECTIONS = frozenset({"GLOBAL", "source", "python"})


def analyze_pants(repo: Path) -> tuple[bool, bool, bool, str | None]:
    """Returns (present, looks_valid, has_backend_section, parse_error).
    An empty (zero-byte) file is present=True, looks_valid=True (an empty
    document is syntactically valid TOML), has_backend_section=False --
    distinct from a non-empty file with no recognizable TOML structure at
    all, which is reported as a parse error."""
    path = repo / PANTS_CONFIG_FILENAME
    if not path.is_file():
        return False, False, False, None
    text, err = read_text_safe(path)
    if err:
        return True, False, False, err
    assert text is not None
    if not text.strip():
        return True, True, False, None
    sections = set(_SECTION_RE.findall(text))
    if not sections and not _KV_RE.search(text):
        return True, False, False, f"{path}: no TOML table header or key=value line found"
    return True, True, bool(sections & BACKEND_SECTIONS), None
