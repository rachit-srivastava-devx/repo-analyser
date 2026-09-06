"""Dependency-version parsing -- package.json (json) and go.mod (line-scan),
each reduced to a plain {name: version} dict for one manifest file.

No external tool, no new dependency: stdlib `json` for package.json; a
plain regex/line-scan for go.mod's `require` declarations. Only these two
formats are parsed for pinned dependency *versions* -- pyproject.toml
(see lint_configs.py; read only for its `[tool.ruff]` table header) and
Cargo.toml (see discovery.py) are never parsed for versions at all, both
for the same no-new-TOML-parser reason.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read_json(path: Path) -> dict:
    """Same contract as repo_type.py's own `_read_json` (missing,
    malformed, and non-dict content all collapse to `{}`) -- reimplemented
    locally rather than cross-imported, per this module's brief."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def package_json_deps(path: Path) -> dict[str, str]:
    """name -> version-range string, `dependencies` + `devDependencies`
    merged (devDependencies wins on key collision -- rare in practice,
    and this is a drift *signal*, not an installer, so exact precedence
    doesn't change the finding). A malformed or empty package.json reads
    as zero dependencies via `_read_json`'s own `{}` fallback -- it
    simply can't contribute to any comparison, it never crashes one."""
    data = _read_json(path)
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            for name, version in section.items():
                if isinstance(name, str) and isinstance(version, str):
                    deps[name] = version
    return deps


# Matches a go.mod `require` entry once the leading `require` keyword and
# any surrounding `(`/`)` block punctuation have been stripped from the
# line -- covers both the single-line `require x v1.2.3` form and the
# multi-line `require (\n\tx v1.2.3\n)` block form with the same pattern,
# since both reduce to "module-path whitespace v-version" per line. Stops
# the version at the next whitespace so a trailing `// indirect` comment
# never leaks into the captured version string.
_GO_REQUIRE_LINE_RE = re.compile(r"^(\S+)\s+(v[0-9]\S*)")


def go_mod_requires(path: Path) -> dict[str, str]:
    """module-path -> version, via a plain per-line regex scan -- not a
    real go.mod parser (this module's stated no-new-dependency
    constraint). `module`/`go`/`replace` directive lines and blank/
    comment/bare-paren lines never match `_GO_REQUIRE_LINE_RE` (they
    don't have a `v<digit>...` second token), so no special-casing beyond
    the one regex is needed. An empty or unreadable go.mod yields `{}`,
    same "found nothing to contribute" shape as `package_json_deps`."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return {}
    requires: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line in ("require (", ")"):
            continue
        line = line.removeprefix("require ").strip()
        m = _GO_REQUIRE_LINE_RE.match(line)
        if m:
            requires[m.group(1)] = m.group(2)
    return requires
