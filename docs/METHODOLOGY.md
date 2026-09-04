# Methodology

Every number this tool produces traces to one of the modules below, each of
which wraps a real, external, independently-verifiable tool or a precisely
defined formula. Nothing here is inferred by a language model reading code
and guessing; every module is deterministic and rerunnable — same commit,
same answer.

## Design principle (CHRONICLE-ADR-001)

A module either returns real computed data, or raises an exception with the
tool's real stderr attached. It never returns an empty or zero result for
something that should have found data. `dependency-cruiser` finding "0
modules" for a directory it should have cruised was exactly this failure
mode during development — see "Known issues found while building this,"
below — and the fix was to treat 0 as suspicious, not as an answer.

## Modules

### `inventory.py` — repo tiering & activity
Plain `git log --all` metadata (hash/author/date/parents), not PyDriller —
this pass needs no diffs, so the lighter tool is used. Two formulas:

- **Tier** by days since last commit: active ≤90, recent ≤365, aging ≤1095,
  dormant >1095.
- **Bus-factor Gini**: `G = (2 * Σ(i * x_i) / (n * Σx_i)) - (n+1)/n`, where
  `x_i` is each author's commit count sorted ascending and `i` is its
  1-indexed rank. G=0 is perfectly even authorship; G→1 is one author owns
  everything.

### `ci_gates.py` — does CI actually run tests?
Parses every `.github/workflows/*.yml`, looks for a step whose `run:` or
`uses:` text matches a test-command pattern (`npm test`, `vitest`, `jest`,
`playwright test`, etc.) or a deploy pattern (docker/ecr/ecs/kubectl). A
repo can have CI configured and still have `any_workflow_runs_tests=False`
— that distinction is the entire point of this module, because "has a
`.github/workflows` folder" is a proxy for "is gated," not the property
itself.

### `ontology.py` — commit classification
Fully deterministic, two-layer rule table (no LLM): (1) if every file a
commit touched matches one unambiguous pattern (lockfile, workflow yaml,
migration, docs, test path), classify by that alone; (2) else match a
conventional-commit prefix or keyword against the subject line; (3)
otherwise `other`, reported as a percentage, never hidden. Priority order
for tie-breaking and the full pattern table are in the module docstring and
`LEAF_PRIORITY`/`KEYWORD_RULES`. Validated by an independent blind audit —
see `ontology_audit_report.md`.

### `escape.py` — defect escape rate (SZZ)
Implements the SZZ algorithm (Śliwerski/Zimmermann/Zeller 2005) directly on
PyDriller + `git blame`, the same technique SZZUnleashed uses:

1. A "fix commit" is any non-merge commit `ontology.py` classifies as
   `bug_fix` or `revert`.
2. For each fix commit's parent, `git blame --line-porcelain` on the
   *deleted* line numbers in each modified file attributes those lines to
   the commit that last touched them — the bug-introducing commit.
3. `escape_rate_12mo(month M) = |commits in M later blamed by a fix landing
   within 365 days| / |all non-merge commits in M|`.
4. `latency_days = fix_commit.author_date - introducing_commit.author_date`.

**Stated limitation**: this is line-based SZZ without the "meta-change"/
line-mapping refinements from SZZ RA (which correct for moved-not-changed
lines and filter cosmetic reformatting). Expect some inflation toward
reformatting-adjacent commits. Pure-addition fix commits (no deleted lines)
carry no blame target and are excluded, reported as
`pure_addition_or_unattributed_fixes` in `escape_summary.json` — not
silently dropped.

### `churn.py` — code-maat (hotspots, coupling)
Wraps `code-maat` (Tornhill, standalone jar), fed a `git log --numstat`
formatted for its `git2` parser. `-a revisions` gives per-file change
frequency (churn); `-a coupling` gives logical/temporal coupling (files
that change together across commits, independent of any import between
them).

### `complexity.py` — cyclomatic complexity & hotspots
Wraps `lizard` for per-function cyclomatic complexity across all languages
in one pass. Hotspot formula (Tornhill): `hotspot_score = total_ccn(file) *
n_revs(file)` — a file that is complex but never changes is low risk; a
file that changes constantly but is trivial is low risk. The product is
where defects concentrate.

### `duplication.py` + `exact_duplicates.py` — two independent duplication measurements
Two different, complementary questions, kept separate rather than
conflated:

- `duplication.py` wraps **jscpd** across the whole portfolio root at once
  (not per-repo) so it can see block-level clones *between* repos, minimum
  10 lines / 70 tokens. Answers: "do these two files share a duplicated
  block."
- `exact_duplicates.py` computes **sha256 of whole-file contents** directly
  (no external tool needed) across the portfolio. Answers a stricter
  question: "is the entire file byte-for-byte identical." A file can share
  a jscpd block with another file while differing elsewhere — conflating
  the two would have overclaimed "N repos have an identical file" when
  only a shared boilerplate block was actually identical. This was caught
  during development by running an actual `diff` on a jscpd-reported
  cluster and finding real per-tenant differences outside the matched
  block — see below.

### `security.py` — gitleaks + semgrep
`gitleaks detect` scans **full git history** per repo (a secret removed in
a later commit is still a leak — a working-tree-only scan would miss it).
`semgrep` with `p/security-audit` + `p/secrets` scans the current tree for
vulnerability patterns. Both are run with `check=False`: their non-zero
exit on finding something is expected behavior, not a tool failure — only
malformed/missing output is treated as an error.

### `depgraph.py` — within-repo import graph
Wraps `dependency-cruiser`. Requires `npm install` to have succeeded
(TypeScript resolution needs `node_modules`); a repo where install failed
is reported with `skipped_reason`, not silently scored as "0 dependencies."
In-degree ranking excludes `node_modules` targets so the "most depended-on
module" statistic reflects internal architecture, not the fact that every
file imports React.

### `testquality.py` — actually running the tests
Executes each repo's unit-test script for real and parses the pass/fail
summary from the runner's own output — not "has a test script" (a proxy)
but "the suite ran and here is what happened" (the property). Scoped to
*unit* tests only: this portfolio's `test:integration:*` scripts need live
AWS/DB/Redis infrastructure unavailable to this analysis, and reporting an
infra timeout as a code defect would be exactly the kind of false claim
this methodology exists to avoid.

### `effort.py` — effort allocation & toil clusters
Per-author and monthly breakdowns of the ontology superclasses, plus
mechanical toil-cluster detection: non-delivery commits are grouped by
(repo, primary directory, superclass) and any group at or above 15 commits
is reported as a candidate cluster worth a human diff-read. `primary_dir`
(persisted per-commit by `ontology.py`) is the most common up-to-2-segment
directory prefix among a commit's touched files. This is a lighter-weight,
fully automated analogue of a hand-audited toil deep-dive — every count is
a real, rerunnable group-by, but no cluster here has had its diffs read by
a human the way a verified finding would.

### `lang.py` + multi-language support
`inventory`, `ci_gates`, `ontology`, `escape`, `churn`, `complexity`, and
`security` are language-agnostic by construction (git-history or
any-language tools). `depgraph`, `testquality`, and `duplication` dispatch
on `lang.detect_repo_language()` (dominant language by file extension
count):

- **depgraph**: JavaScript/TypeScript via dependency-cruiser (as above);
  **Python** via a direct `ast`-based import-graph builder (no external
  tool needed — walks every `.py` file's `Import`/`ImportFrom` nodes and
  matches against the repo's own file-derived module names); **Go** via
  `go list -json ./...` (needs `go.mod` and, ideally, a populated module
  cache). Any other language reports `skipped_reason` explicitly rather
  than a silent empty result.
- **testquality**: JS via `npm run <script>` (as above); **Python** via
  `pytest` (prefers a bare `pytest` on PATH over `python3 -m pytest` — see
  known issues below); **Go** via `go test -json ./...`, whose structured
  per-test pass/fail events are parsed directly rather than regex-matching
  text output.
- **duplication**: `jscpd`'s `--format` list is built from the languages
  actually detected across the portfolio (`lang.JSCPD_FORMAT`) instead of
  a hardcoded JS/TS list.

**Honesty note**: the Python and Go paths in `depgraph.py` and
`testquality.py` were built and verified against small synthetic fixtures
with a hand-computed expected answer (a 3-file Python package with a known
circular import; a 2-package Go module with a known pass/fail test pair) —
not against a real, large-scale polyglot codebase. None was available in
the portfolio this tool was first built against (posx: 100% JavaScript/
TypeScript). Expect rougher edges on unusual project layouts (Python
namespace packages, editable-install src-layouts, Go build-tag-gated
files) than the JS/TS path, which was validated against 26 real repos.

### `deep_reports.py` + `charts.py` + `exec_deck.py` + `pdf_export.py` — the report layer
`deep_reports.py` renders one markdown file per category (matching the
structural pattern of the engagement this tool's format was modeled on: H1
title, an italicized basis/method line citing exact datasets, numbered H2
sections, tables, an "Honest limitations" section, a closing raw-data
citation) — every number in every function is computed fresh from that
run's own CSV/JSON, never hardcoded from a specific run. `charts.py`
renders matplotlib charts in a dark theme matched against real screenshots
of that reference engagement's own chart output (not guessed). `exec_deck.py`
produces one capstone "Slide N / Purpose / Content / Visual / Takeaway"
specification spanning every category — a blueprint for a human or a
slide-design pass to render, not a rendered deck itself. `pdf_export.py`
converts the deep reports + charts into one PDF (markdown → HTML via
`python-markdown`, HTML → PDF via WeasyPrint), dark-themed to match the
embedded chart PNGs seamlessly.

### `synthesize.py` — composite risk ranking
A weighted, min-max-normalized combination of every other module's output
into one ranked list. Documented as a heuristic for prioritization, not a
ground truth — the weights are a stated judgment call (see the module
docstring for the exact formula and weights), changeable by anyone who
disagrees with them, because the raw per-dimension numbers underneath are
the actual evidence.

## Known issues found while building this (and how they were caught)

Keeping this list is itself part of the methodology: a tool that hides its
own construction failures is less trustworthy than one that shows them.

1. **`dependency-cruiser` silently returned 0 modules for a directory
   argument** even with `node_modules` present and a valid `tsconfig.json`.
   Caught by comparing a directory-mode run against an explicit-file-list
   run on the same repo (0 vs 7,585 modules) rather than trusting the first
   answer. Fixed by always passing an explicit file list.
2. **A duplication cluster was almost reported as "9 repos have an
   identical `medusa-config.ts`."** Caught by running a real `diff` between
   two repos in that cluster before writing the finding — they differ
   substantially outside a shared boilerplate block. Fixed by adding
   `exact_duplicates.py` as an independent, stricter measurement and never
   using jscpd's block-match alone to claim whole-file identity.
3. **Backend test suites crashed at require-time on this host's Node v26**
   (`buffer-equal-constant-time`, a transitive dependency of
   `jsonwebtoken`, uses a Buffer internal removed in newer Node). This is
   an execution-environment mismatch, not a defect in the analyzed repos —
   confirmed by checking the repos' own `engines: {"node": ">=20"}` field
   and reproducing clean test runs under Node 20. `testquality.py` pins to
   a detected Node 20 install (via `CHRONICLE_NODE_BIN` env var or an
   auto-detected nvm install) and records `node_version_used` per run
   rather than reporting an environment crash as a test failure.
4. **`dependency-cruiser`, given an explicit file list, still followed
   imports *into* `node_modules`** and reported third-party packages'
   own internal structure as part of the analyzed repo's graph — an
   initial pass nearly reported "800+ circular dependencies" per backend
   repo. Caught by inspecting one actual "circular" edge instead of trusting
   the count: it was entirely inside the `bl` npm package's own
   `readable-stream` shim, unrelated to any application code. Fixed by
   filtering both the module list and each module's dependencies to
   exclude anything resolving into `node_modules` before computing
   `total_modules`, `circular_count`, or `orphan_count` — see `_aggregate()`
   in `depgraph.py`. Real result after the fix: 19 of 20 analyzable repos
   have zero internal circular dependencies.
5. **The vitest all-failed output format has no "N passed" segment**
   (`Tests  1 failed (1)`, vs. the mixed-result format `Tests  3 failed |
   9 passed (12)`), which an initial parsing regex required unconditionally
   — silently producing "0/0/0, unparsed" for every repo where a suite
   failed completely, including four repos independently failing the exact
   same shared i18n test (a real, reportable finding that the bug would
   have hidden). Caught by reading the raw log for a repo the tool claimed
   had an unparseable summary, and finding a perfectly normal one. Fixed by
   testing the corrected regex against all four real observed formats
   directly, in isolation, before re-running the full analysis a third
   time — see `VITEST_TESTS_LINE_RE` in `testquality.py`.
6. **`npm install` modified tracked `package-lock.json`/`yarn.lock` files**
   in the analyzed repos as a side effect (dependency resolution
   normalizing lockfile entries). These are the *analyzed* repos' own
   working trees, not this tool's — left dirty, that's an unintended
   change to someone else's project. Reverted with `git checkout --` after
   installs, verified clean with `git status --porcelain` across every
   repo before considering the run complete.
7. **The Python depgraph import resolver initially collapsed every
   `from package import submodule`-style import onto just `package`**,
   losing the submodule entirely — `ast.ImportFrom.module` alone only
   captures `package`, not the imported name(s). Caught immediately by
   smoke-testing against a synthetic fixture with a hand-computed expected
   graph (a real circular import, `pkg.b` <-> `pkg.c`): the first version
   reported zero circular dependencies and a wrong top-in-degree module.
   Fixed by generating both candidate targets (`package.submodule` and
   `package`) per import and resolving the more specific one first — see
   `_py_imports()` in `depgraph.py`.
8. **The pytest summary-line regex required a leading `===` banner** that
   is not always present (pytest's actual final line is often the bare
   `N failed, M passed in Xs`, with the `===`-wrapped form only appearing
   in some configurations) — caught the same way, by checking the fixture
   run's real raw output before trusting the parsed 0/0/0 result. Fixed by
   making the banner optional and anchoring to line start instead.
9. **`python3 -m pytest` failed with `ModuleNotFoundError` on the machine
   this was built on**, despite a working `pytest` binary being installed
   and on PATH — a multi-Python-install machine (pipx/brew/pyenv) can have
   `pytest` on PATH while the specific `python3` that resolves has no
   pytest in its own site-packages. Fixed by preferring a bare `pytest`
   command when `shutil.which("pytest")` finds one, falling back to
   `python3 -m pytest` only if not.
11. **Mutation testing (Stryker) finally works** -- the fourth attempt
    across two sessions. Root causes of the first three, in order: npx
    package isolation couldn't resolve `typescript`; a stale cached
    binary under the `stryker` name resolved to an abandoned package;
    `npm install` needed `--legacy-peer-deps`; and even after installing
    correctly, the run reported "No tests were executed" because this
    portfolio's `jest.config.js` gates its `testMatch` pattern on a
    `TEST_TYPE` env var Stryker's jest-runner never set. Working recipe
    encoded in `mutation.py`'s module docstring. Real result: the
    portfolio's #1 hotspot file had a 66.7% mutation score with 40% of
    mutants never covered by any test, despite passing tests existing.
12. **osv-scanner's per-vulnerability `severity` field is a full CVSS
    *vector string*** (`"CVSS:3.1/AV:L/..."`), not a number -- the usable
    numeric score is `groups[].max_severity`, a sibling field, matched by
    vulnerability ID. Caught by printing real output before writing the
    parser, not by assuming the field shape.
10. **Design system (The DevX Doctrine, v1.0)**: `charts.py` and
    `pdf_export.py` were restyled to the doctrine's tokens -- Paper/Ink
    palette, one accent (`#1E6FFF`) used only for the headline emphasis word
    and each chart's single focus metric, real Inter Tight / Source Serif 4
    / JetBrains Mono font files bundled in `chronicle/fonts/` (not a system
    sans standing in for them), hairline rules, zero border-radius, zero
    shadows, no table zebra-striping. Two real bugs found applying it:
    (a) every chart was cited by filename in prose ("see charts/x.png")
    but never actually embedded as a markdown image -- no report had ever
    visually shown a chart, caught by looking at a rendered page and finding
    the promised image simply absent; (b) the PDF assembled its sections in
    alphabetic filename order, not the intended narrative sequence, so
    "Commit Ontology" rendered as "Section 01" ahead of "Repository
    Analysis" -- fixed by having `pdf_export.py` import the canonical order
    from `deep_reports.REPORT_SEQUENCE` instead of sorting filenames.
