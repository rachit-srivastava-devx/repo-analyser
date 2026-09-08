"""PII/sensitive-data column-name inventory (static heuristic) -- scans
migration file text for SQL `CREATE TABLE`/`ADD COLUMN` column names and
Django/SQLAlchemy ORM field declarations, matching patterns.py's
PII_NAME_KEYWORDS substring list. Reports counts and locations, never a
judgment on whether the data is actually protected -- same "here's where
to look" spirit as piicatcher's tagging idea, no new dependency (see
package docstring).

Deliberately regex-based, not a real SQL/Python parser for this part
(unlike reversibility.py's AST use) -- a column-name inventory only needs
to find identifier-shaped tokens near a small set of syntactic anchors
(`CREATE TABLE`, `ADD COLUMN`, `models.*Field(`, `sa.Column(`), and a full
parser for three different schema languages is not earned for that.
"""
from __future__ import annotations

import re
from pathlib import Path

from .patterns import PII_NAME_KEYWORDS
from .text_io import read_text_safe

# `col_name TYPE` inside a CREATE TABLE body, or a bare ADD COLUMN.
_SQL_COLUMN_RE = re.compile(
    r'(?:^|,)\s*"?(?P<name>[A-Za-z_][A-Za-z0-9_]*)"?\s+'
    r"(?:VARCHAR|CHAR|TEXT|INT|INTEGER|BIGINT|SMALLINT|BOOLEAN|BOOL|DATE|"
    r"TIMESTAMP|NUMERIC|DECIMAL|SERIAL|FLOAT|DOUBLE|UUID|JSON|JSONB)\b",
    re.IGNORECASE | re.MULTILINE,
)
_SQL_ADD_COLUMN_RE = re.compile(r'ADD\s+COLUMN\s+"?(?P<name>[A-Za-z_][A-Za-z0-9_]*)"?', re.IGNORECASE)
# `name = models.EmailField(...)` -- a models.py-style class-attribute declaration.
_DJANGO_FIELD_RE = re.compile(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*models\.\w*Field\(")
# `("email", models.EmailField(...))` -- CreateModel's own fields=[(name, field), ...] tuple
# shape, as it actually appears inside a *migration* file (distinct from the class-attribute
# style above, which migrations never use for CreateModel/AddField's own field arg).
_DJANGO_FIELD_TUPLE_RE = re.compile(r'''\(\s*["'](?P<name>[A-Za-z_][A-Za-z0-9_]*)["']\s*,\s*models\.\w*Field\(''')
# The `(?<![A-Za-z0-9_])` negative lookbehind stops this matching "model_name="'s
# own trailing "name=" as if it were the AddField(..., name=...) kwarg itself --
# a real false-match this collector's own test suite caught (both kwargs can
# appear on the same AddField(...) call).
_DJANGO_ADDFIELD_NAME_RE = re.compile(
    r"""AddField\([^)]*?(?<![A-Za-z0-9_])name=["'](?P<name>[A-Za-z0-9_]+)["']""", re.DOTALL,
)
_SA_COLUMN_RE = re.compile(r"""(?:sa\.)?Column\(\s*["'](?P<name>[A-Za-z0-9_]+)["']""")


def _is_pii_name(name: str) -> bool:
    lowered = name.lower()
    return any(kw in lowered for kw in PII_NAME_KEYWORDS)


def find_pii_columns(path: Path) -> list[str]:
    """"path:line:column_name" entries for every matched column/field name
    in this one file. A malformed/unreadable file yields an empty list,
    never a crash (AGENTS.md §3 rung 3) -- reversibility.py already
    reports read failures for the same file via its own "unknown" state,
    so this module doesn't need to re-report them."""
    text, err = read_text_safe(path)
    if err or text is None:
        return []
    matches: list[str] = []
    for pattern in (_SQL_COLUMN_RE, _SQL_ADD_COLUMN_RE, _DJANGO_FIELD_RE, _DJANGO_FIELD_TUPLE_RE,
                    _DJANGO_ADDFIELD_NAME_RE, _SA_COLUMN_RE):
        for m in pattern.finditer(text):
            name = m.group("name")
            if _is_pii_name(name):
                line = text.count("\n", 0, m.start()) + 1
                matches.append(f"{path.name}:{line}:{name}")
    return matches
