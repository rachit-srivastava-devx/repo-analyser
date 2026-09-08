"""Monorepo build/task orchestrator detection: which of Nx, Turborepo,
Bazel, Buck2, or Pants a repo uses (if any), plus per-tool static
config-shape signals -- does the config parse, does it look like a real,
configured project graph or a bare scaffold, which schema version it uses
where more than one exists. Mirrors ci_gates.py's/api_contract's own shape
deliberately: presence-and-correctness-of-practice detection from real
repo config files, not live execution of any build/task-graph tool. See
docs/checklist-by-repo-type/monorepo.md's "Build System Health" section
for the full checklist this partially answers, and docs/METHODOLOGY.md for
the exact detection method and known limitations.

Five tools, checked and reported independently -- never averaged into one
score or one "monorepo tool detected" boolean (docs/ARCHITECTURE.md's "two
tools measuring the same thing stay two separate outputs" rule). A repo
mid-migration between orchestrators (e.g. both nx.json and turbo.json
present) reports both; this is a real, common state, not something to
silently resolve to one answer:

  1. **Nx** (`nx_present`/`nx_valid_json`/`nx_has_configured_graph`/
     `nx_project_json_count`) -- does `nx.json` exist and parse as JSON;
     does it define `targetDefaults`, `tasksRunnerOptions`, or
     `namedInputs` (a real, configured project graph vs. a bare scaffold
     default); count of `project.json` files anywhere in the tree as a
     cheap proxy for workspace-project count -- not a full parse of Nx's
     own project-graph algorithm, which needs a live `nx graph` query
     (out of scope, see below).
  2. **Turborepo** (`turbo_present`/`turbo_valid_json`/`turbo_schema`/
     `turbo_task_count`) -- does `turbo.json` exist and parse as JSON;
     does it define a `tasks` (current schema) or `pipeline` (legacy
     schema) key with at least one task, and which schema shape was found.
  3. **Bazel** (`bazel_present`/`bazel_workspace_markers`/
     `bazel_build_file_count`) -- does a `WORKSPACE`/`WORKSPACE.bazel`/
     `MODULE.bazel` file exist at the repo root (all found reported --
     a real bzlmod-migration shape); count of `BUILD`/`BUILD.bazel` files
     anywhere in the tree, bounded scan, filename-only (no Starlark
     parsing).
  4. **Buck2** (`buck_present`/`buck_build_file_count`) -- does
     `.buckconfig` exist at the repo root; count of `BUCK` files anywhere
     in the tree, same filename-only bounded scan as Bazel.
  5. **Pants** (`pants_present`/`pants_valid_toml`/
     `pants_has_backend_section`) -- does `pants.toml` exist and look like
     valid TOML (a bounded structural proxy -- see pants_signals.py's
     docstring for why this repo doesn't carry a TOML-parser dependency);
     does it define a `[GLOBAL]`, `[source]`, or `[python]` section (real
     config vs. a bare stub).

`orchestrators_detected`/`orchestrator_count` summarize which of the five
were found at all (config-file presence, independent of whether that
config parses or is "configured" in the fuller sense above) --
`config_parse_errors` reports a config file that exists but fails to parse
(malformed JSON/an unrecognizable pants.toml), distinctly from "no
orchestrator at all" (`skip_reason`, populated only when none of the five
were found).

**Deliberate v1 scope, stated honestly**: this is static config-file
presence and shape detection only. It does NOT execute `bazel query`,
`nx graph`, `turbo --dry-run`, `buck2 uquery`, or `pants dependencies`
against the repo, and answers none of docs/checklist-by-repo-type/
monorepo.md's other Build System Health criteria -- build-graph
correctness, remote/incremental cache hit rate, cold-vs-warm build time,
cache correctness (false hits), Bazel BUILD-file hygiene via Buildifier,
or Nx/Turbo/Buck2/Pants distributed-execution/utilization health. Every
one of those needs live tool execution against a real build, which this
collector's static-analysis contract (and this pass's scope) does not
cover; see docs/METHODOLOGY.md for the sign-off note.

**Scan-scope limitation, stated honestly**: orchestrator config files
(`nx.json`, `turbo.json`, `pants.toml`, `WORKSPACE`*, `.buckconfig`) are
checked at the repo root only, matching each tool's own convention for
where its workspace-root marker lives. A nested monorepo-within-a-monorepo
whose own workspace config lives below the passed-in repo root is not
found -- BUILD/BUCK/project.json files, by contrast, are counted via a
recursive (bounded) walk since those legitimately live throughout the
tree. A `BUILD`/`BUILD.bazel`/`BUCK` file is counted by filename only;
content is never parsed, so a file that merely shares that name with
unrelated content (e.g. a hand-written build-instructions doc) cannot be
distinguished from a real Bazel/Buck2 BUILD file here.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import MonorepoToolingResult
from .runner import run_monorepo_tooling

__all__ = ["MonorepoToolingResult", "analyze_repo", "run_monorepo_tooling"]
