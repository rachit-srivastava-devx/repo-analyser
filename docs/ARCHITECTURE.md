# Architecture — this tool's own package layout

> Not to be confused with the `ARCHITECTURE.md` mentioned in the README's Limitations section —
> that one is a *per-analysis-run output artifact* (`analyses/<target>/ARCHITECTURE.md`), a manual
> `codebase-memory-mcp` capture of the **target** you point this tool at. This document describes
> **repo-analyser's own** source layout.

## Data flow

```
collectors/*.py  ──write──▶  <out>/*.csv, <out>/*.json   (one file per dimension, per module)
       │                              │
       │                              ▼
       │                     synthesis/synthesize.py  ──▶  <out>/synthesis.json (composite risk ranking)
       │                              │
       ▼                              ▼
graph/knowledge_graph.py     synthesis/deep_reports.py  ──▶  <out>/deep/*.md  (+ reporting/charts.py PNGs)
       │                              │
       ▼                              ▼
<out>/*.graphml            reporting/pdf_export.py  ──▶  <out>/deep/<target>-analysis-report.pdf
```

Every arrow is a **file**, not a function call across subpackages at runtime beyond what's needed
to produce it — `cli.py`'s `run_module()` dispatch is the only place that sequences modules, and
it does so by calling each module's public `run_*()`/`generate_all()` entry point once, in the
order given in `MODULES`. A module never reaches into another module's internals; it reads the
previous module's **output file** from `out_dir`. This is deliberate: it's what makes
`python3 -m repo_analyser analyze <target> --modules deep_reports,exec_deck,pdf` able to
regenerate just the report layer from data already on disk, with no re-scan.

## Subpackage map

| Subpackage | Owns | Depends on | Rule |
|---|---|---|---|
| `core/` | `util.py` (subprocess exec, repo discovery, CSV/JSON I/O, `ToolExecutionError`, `repo_root()`), `lang.py` (language detection, per-module support sets) | nothing else in this package | Every other subpackage depends on this one. This one depends on nothing else here. |
| `collectors/` | One module per measured dimension (`inventory`, `ci_gates`, `ontology`, `escape`, `churn`, `complexity`, `duplication`, `exact_duplicates`, `security`, `depgraph`, `testquality`, `deps_audit`, `lint_quality`, `mutation`, `effort`) | `core/` (+ `ontology.classify_commit` is imported directly by `escape.py` — the one sibling-to-sibling import in the package, because SZZ needs the same commit classification ontology uses) | One collector = one external tool (or git itself) = one CSV/JSON. Never silently empty — raise or `skipped_reason`. |
| `graph/` | `knowledge_graph.py` — assembles a networkx `MultiDiGraph` from collectors' CSVs (duplication, shared-dependency, coupling edges) and exports GraphML | `core/`, reads collectors' output files (not their code) | Pure assembly. Re-scans nothing. |
| `synthesis/` | `synthesize.py` (composite risk ranking), `deep_reports.py` (15 per-category markdown reports, `REPORT_SEQUENCE` defines narrative order — never alphabetical), `exec_deck.py` (capstone briefing spec), `per_repo_digest.py` (one consolidated page per repo — ADR-0003, portfolio-wide vs. per-repo is a deliberate split, not overlap) | `core/`, `reporting/charts` (deep_reports embeds chart PNGs), reads every collector's output | Computes *across* dimensions. No external tool calls here — if you're calling `subprocess`, the code belongs in `collectors/`, not here. |
| `reporting/` | `charts.py` (matplotlib, DevX Doctrine tokens), `pdf_export.py` (markdown → HTML → WeasyPrint, embeds `fonts/`), `report.py` (the plain `REPORT.md` summary, distinct from `deep_reports`'s 15-file suite) | `core/`; `pdf_export.py` imports `synthesis.deep_reports.REPORT_SEQUENCE` to order sections | Presentation only — no analysis logic lives here. |

## Why this split (not "one flat `chronicle/` folder of 25 files")

The flat layout worked while the tool had one author and one target portfolio. It stopped scaling
for three concrete reasons, all real (not hypothetical):

1. **"Which file do I touch to add a new measured dimension?"** had one answer
   (`collectors/<new>.py`, copy the shape of the nearest existing one) that was previously buried
   in a 25-file alphabetical listing next to report-generation code with a completely different
   contract.
2. **Import depth now signals dependency direction.** `collectors/*.py` importing `..core.util` is
   visibly "collectors depend on core"; a flat `from .util import` next to a flat
   `from .deep_reports import` gave no visual signal that one is a foundational dependency and the
   other is a synthesis-layer import that shouldn't be added to a new collector.
3. **Tests mirror this layout 1:1** (`tests/core/`, `tests/collectors/`, ...) — a flat `tests/`
   directory with 25+ files would have had the same discoverability problem the source did.

## Security model

**This tool executes arbitrary code from every repo it analyzes.** That is inherent to what
`testquality`/`mutation` are *for* — actually running a repo's test suite and confirming it
passes, rather than checking that a script named `test` merely exists — and no flag or sandbox
short of full container/VM isolation removes it without also removing the thing being measured.
Documented explicitly here (and in the README, where a new user hits it before running the tool)
rather than left implicit, per the hardcoding/security audit that raised it (docs/METHODOLOGY.md
#28).

Two distinct exposure classes, with different mitigations:

1. **Target-repo code execution — inherent, unmitigated by design.** `testquality._analyze_js_repo`
   runs `npm run <script>` (the repo's own package.json script, which can itself trigger arbitrary
   `pretest`/`posttest` npm lifecycle hooks); `_analyze_python_repo` runs `pytest` directly against
   the repo's own test files; `_analyze_go_repo` runs `go test`, which compiles and executes the
   repo's own Go code. `mutation.py` does the same, plus it *rewrites* the target file with
   synthetic mutants first. All of this runs with whatever privileges are running `repo-analyser`
   itself. There is no CLI flag for this section — the mitigation is operational (see README:
   only point this at repos you already trust, in an environment without access to anything
   sensitive).
2. **Tool-installed-package supply chain — mitigated.** `depgraph._analyze_js_repo` (`npx
   dependency-cruiser`) and `mutation._install_stryker` (`npm install
   @stryker-mutator/core`+runner) both install *this tool's own* chosen, trusted packages, but
   *inside* the target repo's own directory, so peer-dependency resolution sees that repo's
   `node_modules`/`package.json`. That means a compromised target repo's own `.npmrc` (e.g.
   pointing at a different registry) or a dependency-confusion-style local package could otherwise
   try to hijack that install via a postinstall script. Both call sites now pass
   `--ignore-scripts` / the equivalent `npm_config_ignore_scripts=true` env var (`npx` has no
   `--ignore-scripts` flag of its own — verified against `npx --help`, not guessed) — neither
   dependency-cruiser nor Stryker needs install-time scripts to work as a CLI invoked directly via
   its `node_modules/.bin` path. `core.util.run()` grew a generic `extra_env` parameter for this
   (mirroring the existing `extra_path` parameter's shape) since `npx` had no other way to receive
   it.

**Not done, and worth naming rather than leaving implicit**: real isolation (a disposable
container/VM per analysis run, a restricted OS-level user, network egress limits during test runs)
would close exposure class 1. That's a real, valuable next step for anyone running this tool
against repos from outside their own organization — genuinely out of scope for a single-CLI-
invocation tool to silently take on, and not attempted here.

## Adding a new collector (the common case)

1. Copy the shape of the nearest existing collector in `collectors/` (public `run_x(repos: list[Path], out_dir: Path) -> None`, writes one CSV via `core.util.write_csv`, raises `core.util.ToolExecutionError` on real tool failure).
2. Add it to `MODULES` in `cli.py` (and `SLOW_MODULES` if it shells out to something that takes real time).
3. Add the dispatch branch in `cli.py`'s `run_module()`.
4. Add a row to the module table in `README.md`.
5. Add a `tests/collectors/test_<name>.py` with at least: empty input, the tool missing/failing, and one real-shape success case.

## Adding a per-repo digest section (ADR-0003)

For a new fact about an individual repo, not a new collector:

1. Add a `_section_<name>(repo_name, data, ...)` function in `synthesis/per_repo_digest.py`,
   filtering the relevant CSV(s) already loaded in `_AllData` by `repo` (or by whatever column
   identifies that repo — `duplication_clones.csv`'s `repo_a`/`repo_b`, `exact_duplicate_files.csv`'s
   `;`-joined `repos`).
2. Call it from `render_repo_digest`, in narrative order (most decision-relevant first — this is a
   consolidated page someone reads top to bottom, not a reference dump).
3. If the data doesn't exist yet (a planned-but-unbuilt collector, e.g. `performance`), render an
   explicit "not yet measured" line, never a silently-omitted section — same rule as everywhere
   else in this codebase (ADR-0001).
4. Add tests in `tests/synthesis/test_per_repo_digest.py`: the section renders with real data, and
   degrades gracefully with none.
