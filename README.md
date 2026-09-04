# Chronicle Analyzer

Multi-dimensional, reproducible analysis for a git repo or a portfolio of
repos: git-history mining, defect-escape rate, dependency graphs,
duplication, security scanning, and real (executed, not inferred) test
quality — all built on real open-source tools, wired together so every
number in the output traces back to a rerunnable command.

Built for and first run against a 26-repo e-commerce platform portfolio;
nothing in `chronicle/` is specific to that portfolio — point it at any git
repo or directory of repos.

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
| `effort` | Per-author/monthly effort mix, candidate toil clusters | derived from `ontology` |
| `deps_audit` | Known-CVE dependency audit + package staleness | [osv-scanner](https://github.com/google/osv-scanner), `npm outdated` |
| `lint_quality` | Static analysis with each repo's own linter/config | ESLint (JS), [ruff](https://github.com/astral-sh/ruff) (Python), [staticcheck](https://staticcheck.dev/) (Go) |
| `mutation` | Are the tests behaviorally meaningful, not just passing | [Stryker](https://stryker-mutator.io/) (JS/TS only) |
| `knowledge_graph` | A real, exportable graph (duplication + shared-dep + coupling edges) | [networkx](https://networkx.org/) → GraphML |
| `synthesize` | Composite risk ranking across every dimension above | this repo |
| `deep_reports` | One markdown report per category, full depth | this repo |
| `exec_deck` | One capstone "Slide N" briefing spec spanning every category | this repo |
| `pdf` | The deep reports + charts, assembled into one PDF | [WeasyPrint](https://weasyprint.org/) |

Architecture/HLD/LLD (`ARCHITECTURE.md`) is captured separately via
`codebase-memory-mcp` (an LSP-based code knowledge graph tool available in
Claude Code sessions) — not a chronicle-analyzer subprocess. See
**Limitations** below.

**Multi-language**: `inventory`/`ci_gates`/`ontology`/`escape`/`churn`/`complexity`/`security`
work on any language already (git-history or language-agnostic tools). `depgraph`/`testquality`
currently implement JavaScript/TypeScript, Python, and Go; anything else reports
`skipped_reason` explicitly rather than a silent empty result. `duplication`'s `jscpd` format
list is chosen automatically from the languages actually present.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the exact formula
behind every number, including the real bugs found and fixed while
building this (silently-wrong tool output is a documented failure mode,
not hidden) — twelve and counting.

## Design system

Charts and the PDF report follow **The DevX Doctrine** (v1.0): one accent
color (`#1E6FFF`) used sparingly, Paper/Ink palette, real Inter Tight /
Source Serif 4 / JetBrains Mono fonts (bundled in `chronicle/fonts/`),
hairline rules, no rounded corners, no shadows, no table zebra-striping.
`chronicle/charts.py`'s module docstring and `chronicle/pdf_export.py`'s
CSS are the source of truth for the exact tokens.

## Requirements

- Python 3.10+, `pip install -r requirements.txt`
- Node.js + npm (for `duplication`, `depgraph`, `testquality`) — a working
  `npm install` in each target repo is a precondition for `depgraph` and
  `testquality`; `ci_gates`/`ontology`/`escape`/`churn`/`complexity` need no
  install.
- Java (for `churn` — `tools/code-maat.jar` needs a JVM). The jar itself
  isn't committed (see `.gitignore`) — run `bash scripts/setup.sh` once
  after cloning to fetch it (idempotent, safe to re-run).
- `gitleaks` and `semgrep` on PATH (for `security`)
- `jscpd` on PATH (`npm i -g jscpd`), or reachable via `npx`
- If the target repos pin a Node version other than your default, set
  `CHRONICLE_NODE_BIN=/path/to/node20/bin` so `testquality` runs suites
  under the right runtime instead of reporting a version-mismatch crash as
  a test failure (see METHODOLOGY.md, "Known issues").
- For Python targets: `pytest` on PATH (or importable via `python3 -m pytest`).
- For Go targets: `go` on PATH, with the target's dependencies fetchable
  (`go list`/`go test` need a resolvable module cache).
- `matplotlib`, `networkx`, `markdown`, `weasyprint`, `numpy`, `scipy` (in
  requirements.txt) for `deep_reports`/`pdf`/`knowledge_graph` and ad hoc
  statistical analysis — no extra system packages needed beyond `pip install`.
- `osv-scanner` on PATH (for `deps_audit`'s CVE check — `brew install osv-scanner`).
  `npm audit` was tried first and dropped: it hung repeatedly in testing.
- `ruff`/`staticcheck` on PATH, optional (for `lint_quality` on Python/Go
  targets — JS targets use each repo's own installed ESLint, nothing extra needed).

## Usage

```bash
# Analyze a single repo
python3 cli.py analyze /path/to/one/repo

# Analyze a portfolio (a directory whose immediate children are git repos)
python3 cli.py analyze /path/to/org/repos --out analyses/myorg

# Just the fast, no-install-required modules
python3 cli.py analyze /path/to/repos --modules inventory,ci_gates,ontology,escape

# Skip the slow ones (churn/complexity/duplication/security/depgraph/testquality)
python3 cli.py analyze /path/to/repos --skip-slow

# Full depth: every module, then the per-category deep reports and a PDF
python3 cli.py analyze /path/to/repos

# Regenerate just the report layer from data already on disk (fast, no re-scan)
python3 cli.py analyze /path/to/repos --out analyses/myorg --modules deep_reports,exec_deck,pdf

python3 cli.py list-modules
python3 cli.py report analyses/myorg   # regenerate REPORT.md only
```

The PDF (`<out>/deep/<target>-chronicle-report.pdf`) and the capstone deck
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

## Limitations

Nothing in `chronicle/*.py` is hardcoded to any specific repo, org, or
path — every module takes its target as a parameter and computes fresh
from what it finds (verified: zero hardcoded absolute paths in the
codebase). Two real, narrower gaps, stated plainly rather than glossed
over:

- **Language coverage is not universal.** `inventory`/`ci_gates`/`ontology`/
  `escape`/`churn`/`complexity`/`security` work on any language (git-history
  or language-agnostic tools; `complexity` alone covers ~15 languages via
  lizard). `depgraph` and `testquality` are wired for **JavaScript/TypeScript,
  Python, and Go only** — any other language returns an explicit
  `skipped_reason`, never a silent empty/wrong result. `mutation` is
  **JavaScript/TypeScript only** (Stryker); mutmut/PIT exist for Python/Java
  but aren't wired in. `duplication`/`exact_duplicates`/`lint_quality` use an
  explicit extension/linter allowlist — adding a new language is a one-line
  change per module, not an architectural one.
- **`ARCHITECTURE.md` (HLD/LLD/"memory graph") is a manual, one-time capture,
  not a rerunnable module.** It's built by indexing a repo with
  `codebase-memory-mcp` (an interactive tool available in a Claude Code
  session) and saving the result as `architecture_graph.json`/
  `shared_deps.json` in this tool's expected shape — `chronicle/*.py` has no
  subprocess that can invoke that indexer standalone on any machine. The
  report itself is fully data-driven (no hardcoded repo names or numbers —
  it reads whatever was captured), but the *capture step* is manual. Point
  it at a different portfolio and this section will correctly say
  "capture via codebase-memory-mcp first" until you do.
- `knowledge_graph` (the exported `.graphml`) *is* fully automatic and
  re-scans nothing extra — it just assembles CSVs other modules already
  wrote — but it therefore only contains what those modules capture:
  repo-to-repo duplication/shared-package edges and within-repo file
  coupling, not the call-graph-level detail `codebase-memory-mcp` gives you.

## Design rules this codebase follows

- A module returns real data or raises with the real tool stderr attached —
  never an empty/zero result standing in for "didn't work." See
  `chronicle/util.py`'s `ToolExecutionError` and `CHRONICLE-ADR-001` in
  METHODOLOGY.md.
- External tools that exit non-zero on a legitimate finding (gitleaks
  finding a secret, semgrep finding a match, lizard flagging a
  high-complexity function) are called with `check=False` and their
  `returncode` inspected explicitly — never defaulted to "failure."
- Two different tools measuring "duplication" are kept as two separate,
  labeled outputs rather than merged into one number, because they answer
  different questions (see METHODOLOGY.md's duplication section for the
  real example of why this matters).
