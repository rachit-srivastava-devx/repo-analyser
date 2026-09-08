"""go.mod reading -- the Go half of dependency-manifest parsing."""
from __future__ import annotations

import re
from pathlib import Path

# go.mod require-line extraction: matches "<module-path> v<version>",
# whether inside a `require ( ... )` block or a single-line `require path
# version` statement -- both shapes reduce to the same trailing
# "path v1.2.3" token once the optional leading "require" keyword is
# consumed. The repo's own `module foo/bar` declaration and its `go 1.21`
# directive both lack a trailing version token, so neither ever matches.
_GO_REQUIRE_LINE_RE = re.compile(r"^\s*(?:require\s+)?([A-Za-z0-9._~+\-/]+)\s+v\d[\w.\-+]*", re.MULTILINE)


def read_go_mod_modules(repo: Path) -> set[str]:
    gm = repo / "go.mod"
    if not gm.exists():
        return set()
    return set(_GO_REQUIRE_LINE_RE.findall(gm.read_text(errors="replace")))
