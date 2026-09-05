# Repo Analyser

A generalised, reproducible, multi-dimensional analysis tool for a git repo
or a portfolio of repos: git-history mining, defect-escape rate, dependency
graphs, duplication, security scanning, mutation testing, and real
(executed, not inferred) test quality — all built on real open-source
tools, wired together so every number in the output traces back to a
rerunnable command.

Originally built for and first run against a 26-repo e-commerce platform
portfolio; nothing in `src/repo_analyser/` is specific to that
portfolio — point it at any git repo or directory of repos. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the package layout and
[`AGENTS.md`](AGENTS.md) for the operating contract this codebase itself
is held to.

## What it measures

| Module | Question it answers | Tool(s) |
|---|---|---|
| `inventory` | Which repos are active/dormant, who owns them, bus-factor risk | `git log` |
| `ci_gates` | Does CI actually run tests, or just deploy | `.github/workflows` parser |
| `ontology` | What does the work actually consist of (features vs. fixes vs. ops) | deterministic rule classifier |
| `escape` | How often does a bug ship, and how long does it live in prod | SZZ algorithm (PyDriller + `git blame`) |
| `churn` | Which files change most, which files change *together* | [code-maat](https://github.com/adamtornhill/code-maat) |
| `complexity` | Cyclomatic complexity, and complexity×churn hotspots | [lizard](https://github.com/terryyin/lizard) |
| `duplication` | Duplicated code blocks, within and across repos | [jscpd](https://github.com/kucherenko/jscpd) |
| `exact_duplicates` | Byte-identical files across repos (stricter than jscpd) | sha256 |
| `security` | Committed secrets (full history) + vulnerability patterns | [gitleaks](https://github.com/gitleaks/gitleaks), [semgrep](https://github.com/semgrep/semgrep) |
| `depgraph` | Internal import graph, circular dependencies | [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) (JS/TS), `ast` (Python), `go list` (Go) |
| `testquality` | Does the test suite actually pass, right now | real execution: vitest/jest (JS), pytest (Python), `go test` (Go) |
| `e2e_quality` | Does an E2E suite exist, and is it wired into CI (JS/TS only) | Playwright, Cypress, Selenium/WebdriverIO presence + CI step detection |
| `effort` | Per-author/monthly effort mix, candidate toil clusters | derived from `ontology` |
| `deps_audit` | Known-CVE dependency audit + package staleness | [osv-scanner](https://github.com/google/osv-scanner), `npm outdated` |
| `supply_chain` | IaC/Dockerfile misconfigurations + CycloneDX SBOM | [Trivy](https://github.com/aquasecurity/trivy) |
| `lint_quality` | Static analysis with each repo's own linter/config | ESLint (JS), [ruff](https://github.com/astral-sh/ruff) (Python), [staticcheck](https://staticcheck.dev/) (Go) |
| `code_quality` | Keyless SonarQube-style Maintainability Index (Python only) | [radon](https://radon.readthedocs.io/) |
| `mutation` | Are the tests behaviorally meaningful, not just passing | [Stryker](https://stryker-mutator.io/) (JS/TS), [mutmut](https://mutmut.readthedocs.io/) (Python) |
| `knowledge_graph` | A real, exportable graph (duplication + shared-dep + coupling + import edges) | [networkx](https://networkx.org/) → GraphML |
| `synthesize` | Composite risk ranking across every dimension above | this repo |
| `trends` | Regressions/improvements vs. the last run against this same `--out` dir | this repo |
| `deep_reports` | One markdown report per category, full depth | this repo |
| `exec_deck` | One capstone "Slide N" briefing spec spanning every category | this repo |
| `pdf` | The deep reports + charts, assembled into one PDF | [WeasyPrint](https://weasyprint.org/) |

`mutation` picks its own targets: only repos with a fully-passing unit
suite (`testquality`'s output) are eligible, and only the single highest
complexity×churn hotspot **that isn't itself a test file**
(`complexity`'s output) is mutated per repo — see
`select_mutation_targets()` in `chronicle/collectors/mutation.py` (a real
bug this exclusion fixes is documented in that module's docstring).

Architecture/HLD/LLD (a per-target `ARCHITECTURE.md`) is captured
separately via `codebase-memory-mcp` (an LSP-based code knowledge graph
tool available in Claude Code sessions) — not a subprocess this tool
invokes. See **Limitations** below.

**Multi-language**: `inventory`/`ci_gates`/`ontology`/`escape`/`churn`/`complexity`/`security`
work on any language already (git-history or language-agnostic tools). `depgraph`/`testquality`
currently implement JavaScript/TypeScript, Python, and Go; `mutation` implements JavaScript/TypeScript
and Python; anything else reports `skipped_reason` explicitly rather than a silent empty result.
`duplication`'s `jscpd` format list is chosen automatically from the languages actually present.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the exact formula
behind every number, including the real bugs found and fixed while
building this (silently-wrong tool output is a documented failure mode,
not hidden), and [`docs/adr/`](docs/adr/) for the architectural decisions
behind the current shape of the codebase.

## Design system

Charts and the PDF report follow **The DevX Doctrine** (v1.0): one accent
color (`#1E6FFF`) used sparingly, Paper/Ink palette, real Inter Tight /
Source Serif 4 / JetBrains Mono fonts (bundled in
`src/repo_analyser/reporting/fonts/`), hairline rules, no rounded corners,
no shadows, no table zebra-striping. `charts.py`'s module docstring and
`pdf_export.py`'s CSS are the source of truth for the exact tokens.

## Requirements

- Python 3.10+
- Node.js + npm (for `duplication`, `depgraph`, `testquality`, `mutation` on JS/TS) — a working
  `npm install` in each target repo is a precondition for `depgraph` and
  `testquality`; `ci_gates`/`ontology`/`escape`/`churn`/`complexity` need no
  install.
- Java (for `churn` — `tools/code-maat.jar` needs a JVM). The jar itself
  isn't committed (see `.gitignore`) — run `bash scripts/setup.sh` once
  after cloning to fetch it (idempotent, safe to re-run).
- `gitleaks` and `semgrep` on PATH (for `security`)
- `jscpd` on PATH (`npm i -g jscpd`), or reachable via `npx`
- If the target repos pin a Node version other than your default, set
  `REPO_ANALYSER_NODE_BIN=/path/to/node20/bin` so `testquality`/`mutation` run
  under the right runtime instead of reporting a version-mismatch crash as
  a test failure (see METHODOLOGY.md, "Known issues").
- `duplication`'s jscpd scan defaults to a 900s timeout; set
  `REPO_ANALYSER_JSCPD_TIMEOUT=1800` (seconds) or higher for an unusually
  large portfolio — 900s has already proven insufficient twice against a
  real large (Rust+ML) portfolio (see METHODOLOGY.md #30).
- For Python targets: `pytest` on PATH, or (preferred, if present) the
  target repo's own `.venv/bin/pytest` / `venv/bin/pytest` — used
  automatically so the suite runs against the target's own installed
  dependencies rather than whatever `pytest` happens to resolve globally.
- For Go targets: `go` on PATH, with the target's dependencies fetchable
  (`go list`/`go test` need a resolvable module cache).
- `matplotlib`, `networkx`, `markdown`, `weasyprint`, `tabulate` for
  `deep_reports`/`pdf`/`knowledge_graph` — installed automatically via
  `pip install -e .`, no extra system packages needed.
- `osv-scanner` on PATH (for `deps_audit`'s CVE check — `brew install osv-scanner`).
  `npm audit` was tried first and dropped: it hung repeatedly in testing.
- `trivy` on PATH (for `supply_chain`'s IaC misconfig scan + SBOM — `brew install trivy`).
  Deliberately not used for its own CVE-scanning mode — `deps_audit` already owns that via
  osv-scanner against the same lockfiles; running both would duplicate findings under two names.
- `ruff`/`staticcheck` on PATH, optional (for `lint_quality` on Python/Go
  targets — JS targets use each repo's own installed ESLint, nothing extra needed).
- `mutmut` on PATH, optional (for `mutation` on Python targets — JS/TS
  targets install Stryker locally into the target repo automatically).
  **Known platform limitation on macOS**: mutmut's own subprocess
  management can crash a worker via a fork-safety hazard specific to
  macOS + CoreFoundation (unrelated to this tool's own code — see
  `mutation.py`'s module docstring for the full root-cause diagnosis). Not
  observed on Linux CI.

Dev tooling (`pytest`, `ruff`, `mypy`, `mutmut`) installs via the `dev`
extra: `pip install -e ".[dev]"`.

## Security model — read before pointing this at a repo you don't already trust

This tool's core value proposition (`testquality`, `mutation` actually *run* each repo's test
suite rather than checking a script exists) means it **executes arbitrary code from every repo it
analyzes**, with whatever privileges are running it. This is not a bug to be patched — it's the
same trust boundary as running `npm install` or `pip install` on a package you haven't audited,
and there is no flag that removes it without also removing the thing the tool is for:

- `testquality`/`mutation` run each repo's own `npm run <script>` / `pytest` / `go test` —
  arbitrary target-repo code, by design. A malicious test file, or a malicious `pretest`/`posttest`
  npm lifecycle script, runs exactly as it would if the repo's own maintainer ran it.
- `depgraph` and `mutation` additionally install *this tool's own* chosen packages
  (`dependency-cruiser`, Stryker) *inside* the target repo's directory, via `npx`/`npm install`, so
  peer-dependency resolution works against that repo's own `node_modules`. Both calls now pass
  `--ignore-scripts` / `npm_config_ignore_scripts=true` (docs/METHODOLOGY.md #28) so a compromised
  repo's own `.npmrc` or registry config can't hijack that install via a postinstall script — this
  closes one real vector, but does **not** touch the two bullets above.

**Operational guidance**: only run this tool against repos you already trust, on a machine/account
without access to anything sensitive (production credentials, unrelated private repos, cloud
API keys) — the same standard you'd apply before running `npm install` locally. Running it inside a
disposable container or VM with no such access is the safest setup and is not currently automated
by this tool; that would be the natural next step for anyone running this against repos from
outside their own organization. See `docs/ARCHITECTURE.md`'s "Security model" section for the
full per-module breakdown.

## Operational cost — what this actually costs to run

Real numbers from this tool's own portfolio runs, not estimates: a full 24-module run against a
small, 4-repo portfolio took **~2.5 minutes** total wall time. The two slowest modules by far were
`supply_chain` (Trivy, ~45s) and `security` (gitleaks + semgrep, ~27s) — both scan full git
history/filesystem trees, so cost scales with repo size and history depth, not repo count alone.
`duplication` is the one module worth specifically budgeting for on a large or monorepo-style
portfolio: it scans the whole `--out` target's portfolio root in one pass by design (see
`duplication.py`'s own docstring), and this tool's own history includes a real run that needed
**900 seconds** against a large (multi-gigabyte) portfolio — see `REPO_ANALYSER_JSCPD_TIMEOUT`
above.

Two capacity/resource risks worth knowing before a first real run, both encountered directly while
building this tool:

- **`mutation` forks subprocesses of its own** (mutmut on Python, Stryker on JS/TS) — running this
  tool's own analysis loop with any additional concurrency on top of `mutation` specifically is
  deliberately avoided in this codebase's own `core.util.run_concurrent` for exactly this reason
  (see its docstring). mutmut's own fork-safety issue on macOS is documented in
  `mutation.py`'s module docstring and is a real, once-crashed-the-host risk, not a hypothetical
  one — mutmut `>=3.7.0` (this project's own pin) already defaults away from it, but don't run an
  older mutmut against this tool without checking that default first.
- **Don't run this untuned on a memory-constrained machine.** This tool's own concurrency helper
  (`core.util.safe_worker_count`) backs off automatically when `sysctl vm.swapusage` shows real
  swap pressure (6000MB used, the same threshold as a real resource-crisis incident on the machine
  this was built on) — but that only protects *this tool's own* thread pool. It does not, and
  cannot, protect against a separately-running heavy process (another analysis, another tool)
  competing for the same machine's memory at the same time.

## Usage

```bash
# Install (editable, with dev tooling)
pip install -e ".[dev]"
bash scripts/setup.sh   # fetches tools/code-maat.jar, needed by `churn`

# Analyze a single repo
repo-analyser analyze /path/to/one/repo

# Analyze a portfolio (a directory whose immediate children are git repos)
repo-analyser analyze /path/to/org/repos --out analyses/myorg

# Just the fast, no-install-required modules
repo-analyser analyze /path/to/repos --modules inventory,ci_gates,ontology,escape

# Skip the slow ones (churn/complexity/duplication/security/depgraph/testquality/deps_audit/supply_chain/lint_quality/mutation)
repo-analyser analyze /path/to/repos --skip-slow

# Full depth: every module, then the per-category deep reports and a PDF
repo-analyser analyze /path/to/repos

# Regenerate just the report layer from data already on disk (fast, no re-scan)
repo-analyser analyze /path/to/repos --out analyses/myorg --modules deep_reports,exec_deck,pdf

# A module timed out or errored (see run_log.json) -- re-run just that, not the whole portfolio
repo-analyser analyze /path/to/repos --out analyses/myorg --retry-failed

repo-analyser list-modules
repo-analyser report analyses/myorg   # regenerate REPORT.md only
```

Without installing, `python3 -m repo_analyser analyze ...` works the same
way from the repo root (with `src/` on `PYTHONPATH` or after `pip install -e .`).

The PDF (`<out>/deep/<target>-analysis-report.pdf`) and the capstone deck
spec (`<out>/CAPSTONE_DECK.md`) are both derived entirely from the CSV/JSON
every other module already wrote — rerun `deep_reports,exec_deck,pdf` alone
any time you want fresh documents without re-scanning anything.

`analyses/` (all run output) is gitignored — this repo ships the tool, not
one run's findings. A real run's output includes secret-scan fragments and
CVE data that has no business in a public repo; regenerate your own by
running the CLI against your own target.

Output lands in `<out>/`: one CSV or JSON per module, plus `run_log.json`
recording what ran, what failed, and how long each module took. A module
failing does not stop the others — check `run_log.json` for which
dimensions have real data vs. an error to investigate.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=repo_analyser --cov-report=term-missing   # 300+ tests, real subprocess execution where possible
ruff check src/ tests/
mypy src/
```

Tests mirror `src/repo_analyser/`'s layout 1:1 (`tests/core/`,
`tests/collectors/`, ...) and favor real execution over mocks — a real
temp git repo for git-dependent modules, a real `go test`/`pytest`/`mutmut`
run where the tool is available (guarded with `pytest.mark.skipif` so CI
degrades gracefully on a runner missing an optional tool), monkeypatched
subprocess output only for the pure parsing logic of tools that are slow,
non-deterministic, or network-dependent (osv-scanner, gitleaks, semgrep).
See `AGENTS.md` for the full testing philosophy this repo holds itself to.
CI (`.github/workflows/ci.yml`) runs lint, typecheck, and the full test
suite across Python 3.10–3.12 on every push and PR.

## Limitations

Nothing in `src/repo_analyser/**/*.py` is hardcoded to any specific repo,
org, or path — every module takes its target as a parameter and computes
fresh from what it finds. Real, narrower gaps, stated plainly rather than
glossed over:

- **Language coverage is not universal.** `inventory`/`ci_gates`/`ontology`/
  `escape`/`churn`/`complexity`/`security` work on any language (git-history
  or language-agnostic tools; `complexity` alone covers ~15 languages via
  lizard). `depgraph` and `testquality` are wired for **JavaScript/TypeScript,
  Python, and Go only**; `mutation` for **JavaScript/TypeScript and Python
  only** (PIT for Java exists but isn't wired in) — any other language
  returns an explicit `skipped_reason`, never a silent empty/wrong result.
  `duplication`/`exact_duplicates`/`lint_quality` use an explicit
  extension/linter allowlist — adding a new language is a one-line change
  per module, not an architectural one.
- **`ARCHITECTURE.md` (HLD/LLD/"memory graph") is a manual, one-time capture,
  not a rerunnable module.** It's built by indexing a repo with
  `codebase-memory-mcp` (an interactive tool available in a Claude Code
  session) and saving the result as `architecture_graph.json`/
  `shared_deps.json` in this tool's expected shape — nothing in this
  codebase has a subprocess that can invoke that indexer standalone on any
  machine. The report itself is fully data-driven (no hardcoded repo names
  or numbers — it reads whatever was captured), but the *capture step* is
  manual. Point it at a different portfolio and this section will
  correctly say "capture via codebase-memory-mcp first" until you do.
- `knowledge_graph` (the exported `.graphml`) *is* fully automatic and
  re-scans nothing extra — it just assembles CSVs other modules already
  wrote — but it therefore only contains what those modules capture:
  repo-to-repo duplication/shared-package edges and within-repo file
  coupling, not the call-graph-level detail `codebase-memory-mcp` gives you.
- **mutmut on macOS**: a fork-safety hazard in mutmut's own subprocess
  management (unrelated to this tool) can cause a mutant to report as
  "segfault" instead of its real status on macOS specifically — tracked as
  its own status, never silently folded into "killed" or "survived". Not
  observed on Linux.

## Design rules this codebase follows

- A module returns real data or raises with the real tool stderr attached —
  never an empty/zero result standing in for "didn't work." See
  `core/util.py`'s `ToolExecutionError` and
  [`docs/adr/0001-fail-loud-not-silent.md`](docs/adr/0001-fail-loud-not-silent.md).
- External tools that exit non-zero on a legitimate finding (gitleaks
  finding a secret, semgrep finding a match, lizard flagging a
  high-complexity function) are called with `check=False` and their
  `returncode` inspected explicitly — never defaulted to "failure."
- Two different tools measuring "duplication" are kept as two separate,
  labeled outputs rather than merged into one number, because they answer
  different questions (see METHODOLOGY.md's duplication section for the
  real example of why this matters).
- Package layout is split by dependency direction
  (`core → collectors/graph → synthesis → reporting`), not alphabetically —
  see [`docs/adr/0002-src-layout-package-split.md`](docs/adr/0002-src-layout-package-split.md).
