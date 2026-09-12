"""Codebase Structure & Internal Modularity static-signal detection: the
three still-unbuilt rows of docs/checklist-by-repo-type/single-repo.md's
"Codebase Structure & Internal Modularity" section -- module/package size
budget, god class/module detection, and layering/boundary enforcement.
The other three rows in that section (circular dependency detection,
fan-in/fan-out hotspots, configuration & feature-flag debt) are already
covered by depgraph.py and flag_debt/ respectively; this collector does
not rebuild or touch either.

Three signals, checked and reported independently -- never averaged into
one score (docs/ARCHITECTURE.md's "two tools measuring the same thing
stay two separate outputs" rule):

  1. **Module/package size budget** (`oversized_file_count`/
     `oversized_files`/`oversized_package_count`/`oversized_packages`) --
     language-agnostic, no external tool: a pure filesystem walk + line
     count. An oversized file has physical LOC > 500; an oversized
     package is a directory with > 40 source files directly inside it
     (non-recursive). Both are deliberate, documented defaults matching
     common lint-tool conventions (ESLint's `max-lines`, SonarQube
     Community Edition's file-size gate) -- see module_size.py's
     docstring for the exact thresholds as named constants.
  2. **God class/module detection** (`god_class_count`/`god_classes`/
     `god_class_language_supported`) -- Python only for v1, same honesty-
     scoped language-support pattern as depgraph.py's Python/JS/Go split
     (core.lang.GOD_CLASS_SUPPORTED). A class is flagged when its direct
     method count exceeds 20 or its own LOC exceeds 300 (see
     god_class.py's docstring). A repo whose dominant detected language
     isn't Python reports `god_class_count=0`/`god_classes=""` *and*
     `god_class_language_supported=False` -- the boolean exists
     specifically so a caller can't mistake "not supported" for "checked
     and found none" (AGENTS.md §3 rung 9 / §6's "silent empty result"
     failure mode).
  3. **Layering/boundary enforcement** (`layering_tool_detected`/
     `layering_config_path`) -- static config-file presence detection
     only, no external tool invocation, matching monorepo_tooling's own
     "static config presence/shape only" precedent: does a
     dependency-cruiser, import-linter, or go-arch-lint config exist at
     the repo root (see layering.py's docstring for the exact file/
     manifest-key shapes checked per tool). `cargo-modules` (Rust) is
     deliberately not checked -- it's a CLI query tool with no persistent
     config file to detect, stated as an explicit scope exclusion rather
     than silently omitted. This signal has no language-support gate: all
     three tools are checked regardless of the repo's detected dominant
     language, since a leftover config from a past migration is a real,
     checkable fact regardless of what the repo is mostly written in now.

`skip_reason` is populated only for a genuine precondition failure -- the
given path doesn't exist, or isn't a git repository at all. Unlike
migration_hygiene, there is no "no recognized convention" skip case here:
every repo has *some* files, so an all-zero result for a small/empty repo
is a real finding, not something to skip (see analyze.py's docstring).

**Deliberate v1 scope, stated honestly**: god-class detection is
Python-only (no JS/TS/Go/Rust class-shape analysis yet). Layering
detection is presence-of-config only -- it does NOT verify the config
actually runs in CI, that it passes, or that its rules are non-trivial
(an empty/no-op dependency-cruiser config is still reported as
"detected"). `cargo-modules` has no config-presence signal to check by
design, not by oversight. Nothing here executes any of these tools; see
docs/ARCHITECTURE.md's security model for why.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import CodebaseModularityResult
from .runner import run_codebase_modularity

__all__ = ["CodebaseModularityResult", "analyze_repo", "run_codebase_modularity"]
