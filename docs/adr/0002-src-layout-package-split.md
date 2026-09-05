# ADR-0002: `src/repo_analyser/{core,collectors,graph,synthesis,reporting}/` over a flat package

- **Status:** Accepted

## Context

The tool grew from a single-target analysis script into a reusable, generic CLI, and the module
count grew with it: 25 files in one flat `chronicle/` package, differentiated only by filename.
Three concrete problems, observed rather than anticipated:

1. Adding a new measured dimension required scanning a 25-file alphabetical listing to find the
   nearest existing example to copy, with no structural hint about which files were peers.
2. Nothing in an import statement distinguished "this is a foundational dependency every module
   uses" (`util.py`) from "this is a downstream synthesis import that a new collector should never
   need" (`deep_reports.py`) — both were just `from .x import y`.
3. A flat `tests/` directory was about to inherit the same problem the source had, one level later.

## Decision

Split by **what a module depends on**, which lines up exactly with **what question it answers**:

- `core/` — zero internal dependencies. Subprocess exec, repo discovery, CSV/JSON I/O, language
  detection. Everything else depends on this; this depends on nothing else here.
- `collectors/` — one module per measured dimension, each wrapping one external tool (or git
  itself), depending only on `core/` (plus the one documented sibling import, `escape.py` →
  `ontology.classify_commit`, because SZZ and the ontology module must agree on what a "fix
  commit" is).
- `graph/` — the cross-repo knowledge graph, assembled from collectors' output files, not their
  code.
- `synthesis/` — composite analysis computed *across* collectors' output (risk ranking, the
  per-category deep reports, the exec deck). No external tool calls belong here; if a synthesis
  module starts calling `subprocess`, that logic belongs in `collectors/` instead.
- `reporting/` — presentation only (charts, markdown, PDF). No analysis logic.

Package renamed `chronicle` → `repo_analyser` in the same change (the tool stopped being specific
to the `chronicle_button` engagement it was modeled on well before this restructuring; the package
name had not caught up). See the repo rename generally: local folder `chronicle-analyzer` →
`repo-analyser`, matching the already-published GitHub remote name.

## Consequences

- Every internal relative import gained a directory level (`.util` → `..core.util` from inside
  `collectors/`), a mechanical but blast-radius-wide change across all 20 previously-flat modules.
  Verified by importing every module fresh after the move (`python3 -c "import repo_analyser.<x>
  ..."` for all of them) before trusting the restructuring — see the verification log in the PR/
  commit this ADR ships with.
- `churn.py`'s `tools/code-maat.jar` path resolution could no longer assume a fixed
  `Path(__file__).parent.parent` depth (that now resolves to `src/repo_analyser/`, not the repo
  root). Replaced with `core.util.repo_root()`, which walks up to the `pyproject.toml` marker
  instead of counting directory levels — robust to further nesting changes, not just this one.
- `tests/` mirrors this exact layout (`tests/core/`, `tests/collectors/`, ...), so "where does the
  test for X go" has the same one-word answer as "where does X's source go."
- A genuinely new subpackage (a 6th one) is a real decision, not a mechanical one — it goes through
  this same ADR process, not an ad hoc folder.
