"""Dead-code / unreferenced-export detection.

Python via vulture (a pure-AST static analyzer -- verified to need zero
installed dependencies from the target repo; see vulture_runner.py). JS/TS
via a zero-install regex heuristic that flags a top-level export with no
reference anywhere else in the repo's tracked JS/TS files (js_heuristic.py).

v1 scope, deliberately: no Go dead-code analysis and no `knip` for JS/TS --
both would need the target repo's own toolchain resolved (`go mod
download`, `node_modules`) to be accurate, which is a new class of
dependency this v1 does not take on; a real gap, tracked as a follow-up,
not a silent omission.

`unreferenced_export_count_js` is named for exactly what the heuristic can
prove -- never "dead code" -- see js_heuristic.py's docstring for what it
cannot see (dynamic imports, string-based module resolution, etc).
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import DeadCodeResult, Finding
from .runner import run_dead_code

__all__ = ["DeadCodeResult", "Finding", "analyze_repo", "run_dead_code"]
