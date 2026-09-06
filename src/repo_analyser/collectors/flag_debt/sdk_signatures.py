"""Known feature-flag SDK identifiers, and the import-statement shapes that
reveal them. One combined regex covers every supported language's
import/require syntax (see IMPORT_LINE_RE) -- every shape shares the thing
this collector actually cares about: an import-ish keyword, followed
somewhere by a module/package path, checked against a short token list.
That's simpler and just as reliable as a real per-language import grammar
for a first cut -- this collector's whole design brief is regex/text
scanning, not a parser.

Known limitation, stated rather than hidden: this matches per source LINE,
so a JS/TS destructured import of the LaunchDarkly SDK split across several
lines -- an opening brace, an indented client-class name, then a closing
brace plus the module path -- is missed; real usage of these 4 SDKs is
overwhelmingly a single default/namespace import, which does fit on one
line.

(That last paragraph is deliberately worded to describe the multi-line
shape without spelling it out as literal code -- this module's own
docstring is itself a source file IMPORT_LINE_RE scans when this collector
runs against this repo, and an earlier draft that *did* spell out the
literal statement was self-detected as an SDK import by its own docstring.)
"""
from __future__ import annotations

import re

SDK_TOKENS: dict[str, tuple[str, ...]] = {
    "launchdarkly": ("launchdarkly", "ldclient"),
    "split.io": ("splitio",),
    "unleash": ("unleash",),
    "flagsmith": ("flagsmith",),
}

# js_from:     `import ... from "path"` (JS/TS) -- path after "from". Tried
#              FIRST so a named/destructured JS import's local binding name
#              (e.g. "LDClient") never gets a chance to fall through to the
#              generic py_or_java branch and be captured instead of the
#              actual package path.
# py_from:     `from x.y import Z` (Python) -- path is between from/import.
# req:         `require("path")` (JS/Node) or `require "path"` /
#              `require_relative "path"` (Ruby) -- parens optional either way.
# go_line:     `import "path"` (Go, single line).
# py_or_java:  `import x.y.z` / `import static x.y.Z` (Python, Java).
# go_block:    a lone quoted string on its own line -- every line inside a
#              Go `import (...)` block has this shape.
IMPORT_LINE_RE = re.compile(
    r"""     import\s+[^;\n]*?\bfrom\s+['"](?P<js_from>[^'"]+)['"]
        |  ^\s*from\s+(?P<py_from>[\w.]+)\s+import
        |  require(?:_relative)?\s*\(?\s*['"](?P<req>[^'"]+)['"]
        |  ^\s*import\s+['"](?P<go_line>[^'"]+)['"]
        |  ^\s*import\s+(?:static\s+)?(?P<py_or_java>[\w.]+)
        |  ^\s*"(?P<go_block>[^"]+)"\s*$
    """,
    re.VERBOSE | re.MULTILINE,
)


def find_sdk_import(line: str) -> str | None:
    """Returns the canonical SDK name if `line` looks like an import of a
    known SDK, else None -- an ordinary line of code is the overwhelmingly
    common case here, not an error, so silence is the right default."""
    m = IMPORT_LINE_RE.search(line)
    if not m:
        return None
    module = next((g for g in m.groups() if g), None)
    if not module:
        return None
    module_lower = module.lower()
    for sdk, tokens in SDK_TOKENS.items():
        if any(tok in module_lower for tok in tokens):
            return sdk
    return None
