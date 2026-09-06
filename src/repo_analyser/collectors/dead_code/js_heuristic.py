"""Zero-install JS/TS dead-export heuristic: regex-extract each tracked
file's top-level exports, then check every OTHER tracked file's raw text
for a reference to that name. Zero references anywhere else is a
*candidate* -- reported as `unreferenced_export_count`, never "dead code",
because plain-text scanning can't see dynamic/string-based imports
(`import(someVar)`), resolver-only usage, or a same-named comment/string.
A real parser needs the target repo's own toolchain (node_modules) --
exactly the dependency this v1 is scoped to avoid (see __init__.py).
"""
from __future__ import annotations

import re
from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from .models import Finding

JS_TS_EXTS = (".js", ".ts", ".jsx", ".tsx")
_IDENT = r"[A-Za-z_$][\w$]*"

# `export [default] [async] function|class|const|let|var NAME` -- named exports
# and a *named* default export in one pattern.
_DECL_RE = re.compile(
    rf"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|class|const|let|var)\s+({_IDENT})",
    re.MULTILINE,
)
# `export default NAME;` bare-identifier default; anonymous `export default
# () => {{}}` has no name to track, so it's deliberately not matched.
_DEFAULT_BARE_RE = re.compile(rf"^\s*export\s+default\s+({_IDENT})\s*;?\s*$", re.MULTILINE)
# `export {{ a, b as c }} [from '...']` -- one pattern for a named-export list
# *and* a re-export-from list, so a re-export-only file contributes one entry.
_BRACE_RE = re.compile(r"^\s*export\s*\{([^}]*)\}(?:\s*from\s*['\"][^'\"]+['\"])?\s*;?\s*$", re.MULTILINE)


def js_ts_files(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*") if p.is_file() and p.suffix in JS_TS_EXTS
            and not any(part in EXCLUDE_DIR_PARTS for part in p.parts)]


def _line_of(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def extract_exports(content: str) -> dict[str, int]:
    """name -> line of first occurrence. A dict (not a list) so a name
    matched twice (another pattern, or repeated in a brace list) is
    counted once -- the "don't double-count re-exports" contract."""
    names: dict[str, int] = {}
    for pattern in (_DECL_RE, _DEFAULT_BARE_RE):
        for m in pattern.finditer(content):
            names.setdefault(m.group(1), _line_of(content, m.start()))
    for m in _BRACE_RE.finditer(content):
        for token in m.group(1).split(","):
            token = token.strip()
            if not token:
                continue
            name = token.split(" as ", 1)[-1].strip() if " as " in token else token
            names.setdefault(name, _line_of(content, m.start()))
    return names


def _referenced_elsewhere(name: str, other_content: str) -> bool:
    # lookaround, not \b: JS identifiers may contain '$', which \b (a \w
    # boundary) does not treat as part of the word.
    return re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", other_content) is not None


def scan_repo(repo: Path, files: list[Path]) -> list[Finding]:
    contents: dict[Path, str] = {}
    for f in files:
        try:
            contents[f] = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    findings = []
    for f, content in contents.items():
        names = extract_exports(content)
        if not names:
            continue
        other_content = "\n".join(c for other, c in contents.items() if other != f)
        for name, line in sorted(names.items()):
            if not _referenced_elsewhere(name, other_content):
                findings.append(Finding(language="javascript", kind="unreferenced_export",
                                         file=str(f.relative_to(repo)), line=line, name=name))
    return findings
