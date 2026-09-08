# Methodology

Every number this tool produces traces to one of the modules below, each of
which wraps a real, external, independently-verifiable tool or a precisely
defined formula. Nothing here is inferred by a language model reading code
and guessing; every module is deterministic and rerunnable — same commit,
same answer.

## Design principle (docs/adr/0001-fail-loud-not-silent.md)

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

### `api_contract/` — API/schema contract-discipline detection
Answers `docs/checklist-by-repo-type/single-repo.md`'s "Interface & API
Contract Stability" row via four independent, static signals — same
"presence and correctness of practice, not live execution" shape as
`ci_gates.py`:

1. **Spec presence** (`has_spec`/`spec_kinds`/`spec_file_count`/
   `spec_files`): OpenAPI/Swagger (conventional root/docs/api filenames,
   plus a bounded glob for an unconventionally-named file whose content
   still parses as a dict with `openapi`/`swagger` + `paths` keys), GraphQL
   SDL (`.graphql`/`.gql`/`.graphqls` files anywhere), or Protobuf (`.proto`
   files anywhere). All kinds found are reported, not just the first.
   Walks the real filesystem (like `depgraph.py`/`duplication.py`), not
   `git ls-files` — a gitignored-but-present spec file still counts; this
   is a deliberate choice, not an oversight, matching how every other
   filesystem-walking collector already treats `EXCLUDE_DIR_PARTS` as the
   only exclusion rule.
2. **CI breaking-change gating** (`has_breaking_change_check`/
   `breaking_change_tools`): parses `.github/workflows/*.yml` and matches a
   `run:`/`uses:` step's text against six known tools' real command shape
   (`oasdiff breaking`, `buf breaking`, `graphql-inspector`, etc.), after
   stripping bash comment lines — narrows, does not eliminate, the false
   positive of an `echo`/string step that merely *mentions* a tool by name.
3. **Contract-test tooling** (`has_contract_test_tooling`/
   `contract_test_tools`): Dredd/Prism/Schemathesis/Pact detected via
   dependency-manifest entries (`package.json`, `requirements.txt`,
   `pyproject.toml`), known config files/dirs (`dredd.yml`, `pacts/`), or a
   matching CI step — any one of the three is sufficient.
4. **Deprecation + sunset convention** (`deprecated_with_sunset_count`/
   `deprecated_without_sunset_count`): regex scan of each detected spec
   file's raw text for a deprecation marker (`deprecated: true`,
   `@deprecated`, `[deprecated = true]`), then a small line-window search
   around each marker for a sunset signal (`x-sunset`, `x-deprecated-date`,
   the word "sunset", or a bare ISO-date-shaped string) — clipped so it
   never crosses into a *different* deprecation marker's own line (a
   real bug caught while building this: two deprecated fields declared a
   few lines apart let one's real sunset date get misattributed to its
   undated neighbor before the window was clipped at the midpoint between
   markers).

`spec_parse_errors` reports a spec file that exists but fails to parse,
distinctly from "no spec at all" — a malformed file must not crash the
collector run, and the deprecation scan still runs against it as plain
text regardless (the marker/sunset convention is textual, not structural).

**Known limitations, stated plainly**: v1 is static detection only — it
does not execute oasdiff/graphql-inspector/buf/Dredd/Schemathesis/Pact
against two live schema versions or a running service, only checks whether
the repo is configured to. The OpenAPI content-check is a single bounded
glob keyed on the filename containing "openapi"/"swagger"; a spec with a
completely unrelated filename and no conventional path is not found. The
CI-comment-stripping narrows but does not eliminate the false positive of
an `echo "todo: run oasdiff"`-shaped step being read as a real invocation.

### `monorepo_tooling/` — build/task orchestrator detection
Answers part of `docs/checklist-by-repo-type/monorepo.md`'s "Build System
Health" section via five independent, static config-presence-and-shape
signals — same "presence and correctness of practice, not live execution"
shape as `ci_gates.py`/`api_contract`:

1. **Nx** (`nx_present`/`nx_valid_json`/`nx_has_configured_graph`/
   `nx_project_json_count`): `nx.json` existence and JSON validity, whether
   it defines `targetDefaults`/`tasksRunnerOptions`/`namedInputs` (a real,
   configured project graph vs. a bare scaffold default), and a count of
   `project.json` files anywhere in the tree as a cheap workspace-project
   proxy — not Nx's own project-graph algorithm.
2. **Turborepo** (`turbo_present`/`turbo_valid_json`/`turbo_schema`/
   `turbo_task_count`): `turbo.json` existence and JSON validity, and
   which pipeline-definition schema it uses — `tasks` (current, Turbo
   ≥2.0) or `pipeline` (legacy) — reported, not silently resolved, since a
   repo mid-migration between the two is a real state.
3. **Bazel** (`bazel_present`/`bazel_workspace_markers`/
   `bazel_build_file_count`): presence of `WORKSPACE`/`WORKSPACE.bazel`/
   `MODULE.bazel` at the repo root (all found are reported — a bzlmod
   migration can have more than one), plus a bounded, filename-only count
   of `BUILD`/`BUILD.bazel` files anywhere in the tree. No Starlark
   parsing.
4. **Buck2** (`buck_present`/`buck_build_file_count`): `.buckconfig`
   presence at the root, plus a bounded, filename-only count of `BUCK`
   files anywhere in the tree.
5. **Pants** (`pants_present`/`pants_valid_toml`/
   `pants_has_backend_section`): `pants.toml` existence and a bounded
   structural proxy for TOML validity (at least one `[section]` header or
   `key = value` line — not full grammar validation, since this codebase
   deliberately carries no TOML-parser dependency, the same call already
   made by `collectors/repo_type/fileio.py`'s `read_toml_has_table` and
   `collectors/license_compliance/manifest_toml_licenses.py`), and whether
   a `[GLOBAL]`/`[source]`/`[python]` section is declared (real config vs.
   a bare stub).

`orchestrators_detected`/`orchestrator_count` report every tool whose
config file is present, independent of whether it parses; a repo with more
than one (a real migration state) reports all of them, never just the
first. `config_parse_errors` reports a config file that exists but fails
its own validity check, distinctly from "no orchestrator at all"
(`skip_reason`, populated only when none of the five are present).
Orchestrator config-file presence is checked at the repo root only
(matching each tool's own workspace-root convention, and `ci_gates.py`'s
own root-only `.github/workflows` precedent); `BUILD`/`BUCK`/
`project.json` files are counted via a single bounded recursive walk
(`fs_scan.py`, one `rglob` pass regardless of how many tools are being
checked for) since those legitimately live throughout the tree.

**Known limitations, stated plainly**: v1 is static config-presence-and-
shape detection only. It does not execute `bazel query`/`nx graph`/
`turbo --dry-run`/`buck2 uquery`/`pants dependencies`, and it answers none
of the checklist's other Build System Health criteria — build-graph
correctness, remote/incremental cache hit rate, cold-vs-warm build time,
cache correctness (false hits), Bazel BUILD-file hygiene via Buildifier,
or Nx/Turbo/Buck2/Pants distributed-execution/utilization health. Every one
of those needs live tool execution against a real build; no sign-off is
available for them from this pass. A `BUILD`/`BUILD.bazel`/`BUCK` file is
counted by filename only — content is never parsed, so a file that merely
shares that name with unrelated content cannot be distinguished from a
real Bazel/Buck2 BUILD file. A nested monorepo-within-a-monorepo whose own
workspace config lives below the passed-in repo root is not found, by the
same root-only-config-file design as above.

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
    / JetBrains Mono font files bundled alongside `charts.py`/`pdf_export.py`
    in `reporting/fonts/` (not a system sans standing in for them), hairline
    rules, zero border-radius, zero shadows, no table zebra-striping. Two
    real bugs found applying it: (a) every chart was cited by filename in
    prose ("see charts/x.png") but never actually embedded as a markdown
    image -- no report had ever visually shown a chart, caught by looking
    at a rendered page and finding the promised image simply absent; (b)
    the PDF assembled its sections in alphabetic filename order, not the
    intended narrative sequence, so "Commit Ontology" rendered as "Section
    01" ahead of "Repository Analysis" -- fixed by having `pdf_export.py`
    import the canonical order from `deep_reports.REPORT_SEQUENCE` instead
    of sorting filenames.
13. **The src-layout restructuring (ADR-0002) broke two error-handling
    paths that nothing exercised until real tests forced them.**
    `churn.py` and `complexity.py` each had a second, *indented*
    `from .util import write_json` inside their `if errors:` branch --
    invisible to a grep for line-start imports, and to an import-time
    smoke test, because it only executes when a repo actually errors
    during analysis. Caught by writing (and running) a test that
    deliberately triggers that branch. Lesson: an import-time smoke test
    proves a module *loads*; it proves nothing about code paths gated on
    runtime conditions.
14. **A pytest collection error was silently miscounted as a failed test.**
    `pytest --tb=no -q` on a file with a bad import prints "N error(s)
    during collection", which matched the generic summary regex's
    `errors` group -- reporting `tests_failed=1, tests_total=1` for a run
    where *zero* tests actually executed (pytest aborts the whole session
    on a collection error, not just the broken file, confirmed by
    observing a real passing test alongside a broken-import file still
    report 0 executed). Indistinguishable, to a report reader, from "one
    real test ran and failed an assertion" -- exactly the failure class
    this tool's own ADR-0001 exists to prevent, found in itself. Fixed
    with a dedicated `PYTEST_COLLECTION_ERROR_RE` checked before the
    generic summary parse.
15. **`testquality.py` resolved a bare `pytest` from `PATH`, not the
    target repo's own virtualenv** -- found by running this tool on
    itself: every test file failed to import `repo_analyser` because the
    global `pytest` had no idea this project's package existed, reporting
    (correctly, per #14's fix) "19 errors during collection" for a repo
    whose own 300-test suite genuinely passes under its own `.venv`. Same
    principle `lint_quality.py` already applied to ESLint (a repo's own
    installed tool beats a global one); `_pytest_command()` now prefers
    `<repo>/.venv/bin/pytest` / `<repo>/venv/bin/pytest` when present.
16. **Mutation testing picked a test file as its own mutation target.**
    `select_mutation_targets()` chose the single highest
    complexity×churn hotspot with no regard for whether that file *was*
    a test -- on this tool's own (test-heavy) portfolio, that hotspot was
    `tests/collectors/test_churn.py`, and mutating a test file answers
    nothing (there's no separate source left for its own now-mutated
    assertions to have an opinion about). Fixed by excluding files
    matching `core.lang.TEST_FILE_RE` (promoted from a pattern that used
    to live only in `ontology.py`, now shared) before ranking hotspots.
17. **mutmut 3.3.1's real status vocabulary and config keys, grounded by
    running it, not by reading the deprecation warning text.** Two
    findings: (a) a whole file with *zero* test coverage at all makes
    mutmut abort early ("Stopping early, because we could not find any
    test case for any mutant") and report every mutant as `not_checked`
    -- a different status than the per-mutant `no tests` case, and one
    this tool's parser didn't originally bucket anywhere, silently
    vanishing from every counted total. (b) mutmut's own deprecation
    warning suggests renaming `paths_to_mutate` to `source_paths` in
    `setup.cfg` -- doing so was tried, and it broke every real run
    ("please specify it by adding paths_to_mutate=... in setup.cfg"),
    caught immediately by the test suite. Kept the deprecated-but-working
    key rather than trust the warning's suggested replacement unverified.
18. **A macOS-specific fork-safety crash, root-caused via a real crash
    report, not dismissed as flakiness.** An obviously-killable mutmut
    mutant intermittently reported "segfault" (exit code -11) instead of
    "killed". The macOS crash reporter's own report pinpointed the exact
    cause: `*** multi-threaded process forked *** / crashed on child side
    of fork pre-exec`, inside `_setproctitle` calling into CoreFoundation
    -- a well-known hazard (Objective-C runtime / CoreFoundation is not
    fork-safe from a multithreaded parent without an immediate `exec()`),
    the same reason CPython's own `multiprocessing` defaults macOS to
    `spawn` instead of `fork`. Not a bug in this tool or in mutmut's
    result-parsing; tracked as its own `segfault` status, never folded
    into "survived" or "killed". At the time this was written the blast
    radius looked contained to one mislabeled status per mutant -- it
    was not. See #23: this same crash brought down the whole host during
    the first real portfolio-scale run.
19. **`testquality.py`'s Python path replaced three hand-written regexes
    (`PYTEST_SUMMARY_RE`, `PYTEST_NO_TESTS_RE`, `PYTEST_COLLECTION_ERROR_RE`)
    with pytest's own `--junit-xml` structured output**, parsed via stdlib
    `xml.etree.ElementTree`. This wasn't a style preference: one of those
    three regexes existed *specifically* to patch around a miscount the
    other two caused (a collection error's prose matched the generic
    summary regex's `errors` group). JUnit XML reports `errors` and
    `failures` as separate, unambiguous integer attributes on the
    `<testsuite>` element -- the exact distinction three regexes were
    reconstructing from human-readable text, given for free by an
    interface pytest already ships and maintains. Verified safe by
    running all 30 existing testquality tests (including the two
    regression tests for the original miscount bug) against the new
    implementation with zero test changes -- same external behavior,
    structurally sounder internals.
20. **Two hand-rolled markdown-table builders (`deep_reports._md_table`
    and `report._table`) replaced with the `tabulate` library**, and both
    gained pipe-character escaping neither the old code nor tabulate's
    own github format applied automatically -- a commit subject, semgrep
    message, or file path containing a literal `|` would otherwise
    silently corrupt a table's column structure. Found while auditing the
    codebase for hand-rolled logic that a stable, already-installed-
    adjacent library already solves correctly.
21. **`report.py`'s "Test quality" section read a JSON key
    (`repos_with_test_failures`) that `testquality.py` has never written**
    -- the real key is `repos_with_real_test_failures_right_now`. Found
    by cross-referencing the read side against the write side while
    auditing report.py for the tabulate swap above. `.get(key, 0)`
    silently returned the default on every single run since this line was
    written: REPORT.md's "N repos have failing tests RIGHT NOW" line has
    always read **0**, regardless of the real number, for every portfolio
    this tool has ever been pointed at. Caught only because the audit
    happened to read both sides of that boundary in the same pass -- had
    zero test coverage before this fix (see `tests/reporting/test_report.py`,
    added in the same change, including a regression test with a nonzero
    real value to prove the read side actually connects to the write side
    now).
22. **Four independently hand-maintained "exclude these directories" lists
    had drifted out of sync**: `core/lang.py`, `depgraph.py` (two of its
    own, one per language path), `complexity.py`, and `exact_duplicates.py`
    each kept a separate copy, and only `core/lang.py`'s covered
    `venv`/`.venv`/`__pycache__`/`vendor`/`target`. Found while preparing
    to point this tool at a real portfolio containing multi-GB Rust repos
    (`target/` build directories) for the first time -- `complexity.py`
    would have handed lizard thousands of files of compiled-dependency
    source copies. Consolidated onto `core.lang.EXCLUDE_DIR_PARTS` as the
    one source of truth; each module now derives its own needed shape
    (a glob list for lizard's `-x` flag, a plain set for the others) from
    it instead of maintaining an independent copy. Regression tests added
    for both previously-uncovered directories (`target/`, `.venv/`) in
    both previously-affected modules.
23. **#18's "segfault" crash escalated to a real kernel panic during the
    first full-portfolio mutation run (2026-09-04), taking the whole host
    down.** Not a metaphor, and not diagnosed by inference: the panic log
    (`/Library/Logs/DiagnosticReports/Retired/panic-full-*.panic`) gives
    the literal reason -- `panic(...): watchdog timeout: no checkins from
    watchdogd in 91 seconds` -- with `memoryStatus` showing 14MB free RAM
    and kernel_task threads blocked on a contended mutex at the moment of
    panic, and 11 matching SIGSEGV `.ips` crash reports in the 20 minutes
    before it, all with the identical stack from #18
    (`_setproctitle` -> `CFBundleGetFunctionPointerForName` ->
    `os_log_type_enabled`), all children of this tool's own process
    coalition. Root cause: `_analyze_python_repo` invoked bare `mutmut`
    off `PATH` with no control over whether the resolved version disabled
    `setproctitle`'s fork-unsafe behavior on Darwin -- mutmut>=3.7.0
    defaults `use_setproctitle` to `False` on macOS
    (`boxed/mutmut#450`), but this tool never asserted that itself, so it
    was exposed to whatever version happened to be installed. Fix:
    `_mutmut_setup_cfg_text` now writes `use_setproctitle=False` into the
    generated `[mutmut]` section explicitly, verified against mutmut's
    own `configuration.py` (`setup_cfg_conf`'s boolean parsing accepts
    it) rather than left to a version- and platform-detection-dependent
    default. This is the one finding in this log that isn't "the report
    was wrong" -- it's "the tool that produces the report can crash the
    machine running it," which is why it gets its own entry instead of
    just amending #18.
25. **`duplication.py`'s jscpd timeout (300s) was too tight for a real
    large portfolio.** Found the same day as #23/#24, on the first full
    run against Principal Engineering (a Rust+ML portfolio): jscpd timed
    out at exactly 300s and the whole `duplication` module was recorded
    as failed, even though the other 19 modules in the same run completed
    fine -- a real scalability ceiling, not a crash or a parsing bug.
    Bumped to 900s. Still a hard ceiling (this tool does not do unbounded
    subprocess waits), just a more realistic one for a portfolio-root
    scan, which by this module's own design has no natural size cap.
24. **mutmut drifted from 3.3.1 (what this integration was grounded
    against) to 3.7.0 in this environment, silently, via an unpinned
    dependency -- and the real-execution test suite caught it.** Found
    while re-verifying #23's fix: `test_real_run_produces_internally_
    consistent_counts` went red with `ran=False`, `skip_reason='mutmut
    produced no parseable results'`, even though the run itself
    succeeded. 3.7.0 replaced 3.3.1's CLI with a Textual-based progress
    UI and changed `mutmut results`' default to print nothing; the fix
    (confirmed against the actual installed binary's `--help` output, not
    guessed) is `mutmut results --all true`, which reproduces the exact
    `<qualified_name>: <status>` line format this tool's regex already
    parses. Two lessons: an unpinned dependency in a tool that shells out
    to real binaries is itself a correctness risk, not just a mutation-
    testing-specific one -- and the reason this was caught at all is that
    the real-execution test actually runs mutmut end to end instead of
    asserting against a recorded fixture.
26. **`mutation.py`'s `_analyze_js_repo` hardcoded `testRunner: "jest"` in its
    Stryker config unconditionally, with zero detection.** Found by an
    independent hardcoding audit (a subagent that actually ran this CLI
    against fresh throwaway repos to prove `discover_repos()` itself is
    generic, then read every collector for the same class of bug).
    `testquality.py` already had the correct jest-vs-vitest detection --
    check whether the repo's own chosen unit-test script body contains
    "vitest" or "jest" -- but mutation.py never used it, so pointing this
    tool at a vitest repo would install Stryker's jest plugin regardless,
    which reports "No tests were executed" and gets recorded as an ordinary
    skip -- not loud, so it would go unnoticed in a real report rather than
    erroring. Fix: the shared detection (now `detect_js_test_runner`) and
    the script-selection it depends on (now `pick_unit_script`) were moved
    out of testquality.py into `core/lang.py` so both modules read
    package.json's chosen script the same way and can never disagree about
    which runner a repo uses. `_analyze_js_repo` now detects the real
    runner, installs the matching Stryker plugin
    (`@stryker-mutator/vitest-runner` vs `@stryker-mutator/jest-runner`,
    grounded against Stryker's own vitest-runner docs, not guessed), and
    builds a runner-shaped config: jest needs its `configFile` spelled out
    explicitly (point 3 above), vitest auto-discovers its own config file
    and none is guessed for it here -- hardcoding one would just be this
    same bug again for a repo that names its vitest config differently. An
    undetectable runner is now a named skip reason instead of a silent
    wrong guess. Verified end to end against two real, from-scratch fixture
    repos (not just mocked unit tests): a jest fixture reproduced the
    pre-existing working path (3/3 mutants killed, 100% score, confirming
    no regression), and a vitest fixture -- the actual new capability --
    initially still failed for real, with `"No tests were executed"`, even
    with the runner correctly detected as vitest and the correct plugin
    installed. The real Stryker log named the exact cause: `"Vitest failed
    to find test files related to mutated files"` -- Stryker's vitest
    runner defaults `related: true` (only run tests it thinks are related
    to the mutated file) and its own detection failed even though the
    fixture's one test file directly imports the one source file, a
    documented Stryker unreliability (see its troubleshooting page), not
    a bug in this tool's config-building. Since this tool mutates arbitrary
    target repos it doesn't control the test-authoring style of, a silent
    "no tests found" is worse than a slower-but-correct full-suite run, so
    the vitest config now explicitly sets `related: False`. Re-verified
    after that change: 2/2 mutants killed, 100% score, `ran=True`, no skip
    reason -- vitest mutation testing now genuinely works, not just
    "detects vitest and stops silently doing nothing."
27. **The same function's `env_extra = {test_type_env: "unit"}`, combined
    with a default `test_type_env: str = "unit"`, set an environment
    variable literally *named* `unit` (value `"unit"`), not `TEST_TYPE=unit`
    as the docstring and #11 both intended.** Found by the same audit.
    Every JS mutation run to date -- including the one that reproduced a
    66.7% mutation score for `posx-mokobara-backend` -- ran with this wrong
    env var, meaning the `TEST_TYPE`-gated `testMatch` trick documented
    above never actually fired via this tool. Whether that specific
    already-recorded score is still correct depends on what
    `posx-mokobara-backend`'s own jest config falls back to with
    `TEST_TYPE` unset -- not re-checked as part of this fix, and worth a
    dedicated re-run before treating that number as final. Fixed by
    changing the default to `test_type_env: str = "TEST_TYPE"`, and the
    whole injection is now scoped to `runner == "jest"` (see #26) --
    vitest has no documented equivalent quirk, so nothing is injected for
    it.
28. **This tool's own security exposure had never been documented, only the
    exposure it *scans for*.** Raised directly by the user, stepping back
    to grade this project against its own operating standard rather than
    just requesting another scanner: `testquality`/`mutation` execute
    arbitrary target-repo code by design (that's what "actually run the
    tests" means), and `depgraph`/`mutation` additionally install this
    tool's own chosen packages (dependency-cruiser, Stryker) *inside* the
    target repo's own directory. Neither is fixable by a flag -- the first
    is inherent to the tool's purpose, the second is a real but narrower
    supply-chain vector (a compromised repo's own `.npmrc`/registry config
    hijacking a trusted package's install via a postinstall script).
    Fixed the narrower one: both install call sites now pass
    `--ignore-scripts` / `npm_config_ignore_scripts=true` (`npx` has no
    `--ignore-scripts` flag of its own, confirmed against `npx --help`
    directly rather than assumed) -- `core.util.run()` grew a generic
    `extra_env` parameter for this, mirroring the shape of its existing
    `extra_path` parameter. The inherent exposure is now documented
    explicitly and prominently (README's own "Security model" section,
    read before Usage; the full breakdown in `docs/ARCHITECTURE.md`)
    instead of living only in a contributor's head -- real sandboxing
    (container/VM isolation per run) is named as the concrete next step
    for anyone running this against untrusted repos, not attempted here.
29. **Every collector ran its per-repo loop strictly sequentially, even
    though each iteration is one I/O-bound subprocess call independent of
    every other repo.** Raised directly by the user: for a 26-repo
    portfolio, that's the wall-clock cost of 26 sequential subprocess
    calls stacked up, mostly spent *waiting*, not burning this tool's own
    CPU. Fixed with a small, capped `ThreadPoolExecutor`
    (`core.util.run_concurrent`) applied to `security`, `complexity`,
    `deps_audit`, `lint_quality`, and `depgraph` -- threads, not
    `multiprocessing`/raw `fork()`, since `subprocess.run()`/`Popen`
    already release the GIL while the child runs, so threads get the
    concurrency benefit with zero new fork-safety surface. `duplication`
    was checked and deliberately left alone: it runs jscpd *once* across
    the whole portfolio root by design (to see duplication *between*
    repos), not once per repo, so there is no per-repo loop to
    parallelize there. `mutation` was checked and deliberately excluded,
    not just left sequential by oversight: mutmut and Stryker each
    already fork their own worker subprocesses internally, and this
    tool's own concurrency on top would multiply the exact fork-crash
    hazard that caused a real kernel panic (#23), not just add load -- a
    one-line comment on `run_mutation` itself says so, so a future change
    doesn't "helpfully" parallelize it. Sized off real resource state
    rather than a fixed worker count: `safe_worker_count` reads
    `sysctl vm.swapusage` (same signal and 6000MB threshold as this
    machine's own `~/.claude/hooks/resource-safety-gate`, grounded against
    the same two real incidents) and falls back to fully sequential when
    swap is already elevated. Also checked, per the user's specific ask:
    whether `core.util.run()` used `preexec_fn` anywhere -- the identical
    fork-before-exec hazard class as #23's crash. It did not (confirmed by
    grep, not assumed); see #30 for what that same check *did* turn up.
30. **A `run()` timeout doesn't actually free the resources it's meant to
    bound if the child spawns its own child.** Found live, not in a lab,
    while re-running `duplication` against the real Principal Engineering
    portfolio to verify #25's timeout bump: the CLI reported jscpd as
    "timed out after 900 seconds" and exited, but the real
    `jscpd-darwin-arm64` binary was still alive 15+ minutes later, `ps`
    showing it reparented to `launchd` (ppid 1) and still burning ~75% CPU
    and 2.9GB RSS -- a genuine still-running orphan, confirmed and killed
    by hand, not inferred. Root cause: plain `subprocess.run(...,
    timeout=...)` only kills the *direct* child it spawned; jscpd's own JS
    entry point had already spawned its native binary as a *grandchild*,
    which the timeout's kill signal never reached. Fixed by switching
    `run()` from `subprocess.run` to manual `Popen`+`communicate()`, with
    `start_new_session=True` (puts the whole tree in its own process
    group) and `os.killpg(...)` instead of `proc.kill()` on timeout --
    deliberately not `preexec_fn=os.setsid`, which would reintroduce the
    identical fork-before-exec hazard class that caused #23's real kernel
    panic; `start_new_session` gets the same process-group result via the
    safe `posix_spawn` path. Verified with a real (not mocked) regression
    test: a `sh -c "sleep 30 & ...; wait"` child that spawns its own
    backgrounded grandchild, timed out at 1s, confirming the grandchild's
    pid is actually gone afterward (`os.kill(pid, 0)` raising
    `ProcessLookupError`), not just that the wrapper exited. A timeout
    that doesn't free its resources is nearly as dangerous as no timeout,
    especially for a tool whose own history includes a real crash from
    uncontrolled subprocess resource use.
31. **The captured raw output for "Stryker produced no mutation.json" was a
    *tail* slice (`combined[-500:]`), which throws away the one line that
    actually names the failure for this branch's most common real
    trigger.** Found while writing this report: `analyses/posx_after/
    FINDINGS.md` §11 documented 3 of 4 real, mutation-eligible posx repos
    crashing with an unresolved error, the captured text starting mid-path
    (`s/rachitsrivastava/...`, `astava/Developer/...`,
    `itsrivastava/Developer/...` -- each cut at a different offset) and
    ending in `innerError: undefined` / `Node.js v20.20.2`, explicitly
    flagged there as "root cause not yet known." That exact shape is a
    textbook Node.js uncaught-exception dump: the real error type and
    message print *first*, then the stack frames, then the engine version
    *last* -- so a tail slice keeps only the frames and version, never the
    line that would have named the actual exception. Not a new run needed
    to confirm this -- the truncation pattern in the already-captured data
    matches the mechanism exactly. Fixed by slicing `combined[:2000]`
    (head, not tail) instead. Doesn't retroactively recover the 3 posx
    repos' actual error text (that data is already gone, overwritten by
    every re-run since), but the next re-run of `ROADMAP.md` §3a will
    surface it directly instead of needing the separate manual
    `--logLevel trace` step that section still recommends as its own
    concrete next step.
32. **`knowledge_graph.py` was "half baked": 2 node types, 3 edge types,
    `SHARES_PACKAGE` npm-only, and it never ingested `depgraph.py`'s own
    already-computed import graph despite that data already existing on
    disk.** Raised by the user directly. Both real, in-scope gaps closed:
    (1) a new `IMPORTS` file&lt;-&gt;file edge, read straight from
    `depgraph_raw/*.json` -- zero new scanning cost, exactly matching this
    module's own stated "reads only files already written by other
    modules" design. Two on-disk shapes needed normalizing: Python/Go's
    own `{"nodes": [...], "edges": [...]}` (already internal-only) and
    JS's raw dependency-cruiser JSON (still has node_modules/external
    noise, filtered via the newly-shared `core.lang.is_internal_js_module`
    -- hoisted out of `depgraph.py`'s `_aggregate()` rather than imported
    cross-collector, since `docs/ARCHITECTURE.md`'s own rule for `graph/`
    is "reads collectors' output files, not their code"). (2)
    `SHARES_PACKAGE` generalized past npm to the same three languages
    `depgraph.py`/`testquality.py`/`mutation.py` already support --
    `requirements.txt` for Python, `go.mod`'s `require` block for Go.
    First attempt gated the reader choice on `detect_repo_language`'s
    dominant-file-extension heuristic and broke an existing test: a repo
    can have a manifest (a real ecosystem) without yet having enough of
    that language's own *source* files to win the file-count vote (true
    of every fixture in this test file, which only ever write a
    `package.json`, never real `.ts` files). Fixed by keying the
    ecosystem off *which manifest reader actually found dependencies*
    instead -- matching the original npm-only code's own simpler "if
    package.json exists, treat as npm" logic, just extended to three
    manifest types. Same-ecosystem-only pairing (not just the pre-existing
    >=5-shared-package floor) also now rules out a same-named package in
    two unrelated ecosystems (npm's and PyPI's own separate "requests")
    ever counting as a real shared dependency. A basic local query helper
    (so the graph is useful without an external tool) was in the same
    backlog item but not built this pass -- GraphML export + Gephi/yEd/
    Neo4j import remains the only way to query it today.
33. **mutmut got pinned exact only *after* its drift broke something real
    (#24) -- nobody had checked whether the same class of risk exists for
    this tool's other external CLI tools.** Raised directly by the user.
    Audited every one: `dependency-cruiser` (via `npx --yes dependency-
    cruiser`, no version at all) was the one real, fixable instance found
    -- an unpinned `npx` call always resolves whatever's latest or
    stale-cached, and this exact module already has its own documented,
    hard-won behavioral quirk (the "silently returns 0 modules for a dir
    arg" note a few lines above `_analyze_js_repo`'s npx call) diagnosed
    and grounded against one specific version, 18.2.0 -- confirmed as the
    real current npm-registry version before pinning to it, not guessed.
    Now pinned: `dependency-cruiser@18.2.0`. `lizard` is a pip dependency
    already declared in `pyproject.toml`, just with a floor and no ceiling
    (`>=1.24`) -- lower risk than an entirely unpinned external CLI, and
    left as-is rather than guessing an upper bound with no observed
    breakage to justify one. `gitleaks`, `semgrep`, `osv-scanner`, and
    `jscpd` are a different, harder case, honestly named rather than
    silently left out: all four are OS-package-manager or global-npm
    installs this Python project has no install-time control over at all
    (README's own Requirements section already says "on PATH" for all
    four) -- pinning them isn't a one-line fix the way the npm-managed
    `dependency-cruiser` call was. The concrete, buildable next step for
    these four: a `--version` check against each on startup, logged (or
    written to run_log.json) against a documented "last verified against"
    version per tool, so a future drift is visible in the output instead
    of silent -- not built this pass.
34. **No E2E test-suite detection.** From the user's original backlog:
    `testquality.py` is deliberately unit-tests-only (its own docstring),
    and `ci_gates.py`'s generic `TEST_RE` already matches `playwright
    test`/`cypress run` as a side effect of asking "did *some* test
    command run" -- but nothing answered "does an E2E suite exist, and
    does CI actually run it" as its own question. New module,
    `e2e_quality.py`: two independent presence signals (package.json
    dependency names; a framework's own conventional config file --
    checked separately since a repo can have either without the other),
    then a framework-specific CI-step regex distinct from ci_gates.py's
    broader one (verified with a real regression test: `npm test` in a
    workflow must NOT count as evidence a Playwright suite specifically
    ran, even though ci_gates.py's own TEST_RE would count it as *some*
    test running). Selenium's own npm package and WebdriverIO (the
    realistic way most JS/TS repos actually reach Selenium/WebDriver
    today) fold into one `selenium/webdriver` family rather than two
    thinly-populated categories. Scope stated honestly: JS/TS only --
    Playwright-Python and Python's own Selenium bindings are real and not
    covered, would need a different signal (requirements.txt/pyproject.toml
    package names) not yet built. Not added to `SLOW_MODULES`: unlike
    every other new-feature addition tonight, this one calls zero
    subprocesses (package.json/config-file/workflow-YAML are all local
    reads), so it belongs with `ci_gates`/`ontology`, not `testquality`.
35. **Added `synthesis/trends.py`: run-over-run regression/improvement
    detection against a saved baseline, closing the last item on the
    user's original backlog** ("self learning loops" -- the existing
    growing bug log in this very file is a static, manual form of that,
    not an automated one). Reads a curated, real subset of fields already
    written by other collectors' own `*_summary.json` files (grounded
    against this run's actual on-disk files, not guessed field names) --
    secrets/CVE/lint-error counts, mean mutation score, duplication
    percentage, escape counts and latency, E2E coverage -- classifies each
    as improved/regressed/unchanged/new against whatever baseline was
    saved in the same `--out` directory last time, then overwrites that
    baseline with this run's own numbers. A real gap found writing this:
    `core.util.read_json` doesn't catch malformed JSON, so a corrupted
    summary file from a prior crashed run would have taken this module
    down with it rather than just reporting that one metric as
    unreadable -- caught by a test that deliberately writes invalid JSON,
    not by inspection.
36. **`duplication.py`'s jscpd timeout (#25/#30) had been bumped 300s ->
    900s -> 1800s, failing all three times against the same real
    portfolio -- and the actual cause was never the timeout value.**
    Found while re-running it for this report: `du -sh` on the two large
    repos in that portfolio showed `fleet-rs` at 3.3GB and `fleet` at
    1.8GB, both containing multi-gigabyte `target`/`var`/`vendor`
    directories -- and both repos' own `.gitignore` files explicitly
    exclude exactly those directories (Rust build output, runtime logs,
    vendored dependencies). `run_duplication`'s jscpd invocation passed
    `--no-gitignore`, with no rationale surviving anywhere in this
    codebase's own decision log, forcing jscpd to scan gigabytes of
    generated/vendored content its own maintainers had explicitly marked
    as not real source -- a self-inflicted scan-scope explosion, not a
    genuine "this much real code takes this long" ceiling. Removed the
    flag; jscpd's own default already respects `.gitignore`, which is
    what real source-only duplication scanning wants. Verified with a
    real (not mocked) end-to-end test: a block duplicated between a
    tracked file and a `.gitignore`d one, in an actual git repo (jscpd's
    gitignore-handling needs a real `.git` present to mean anything, same
    as git itself), is no longer reported as a clone. Re-run against the
    real portfolio queued after this fix to confirm it resolves the
    timeout for real, not just in a synthetic fixture -- confirmed: the
    same real portfolio that had failed at 300s, then 900s, then 1800s
    completed in **4.5 seconds**, a ~400x reduction, conclusive
    confirmation this was the actual cause all along.
37. **Added `code_quality.py`: a keyless SonarQube Quality Gate stand-in**,
    the last item on the user's original backlog. SonarQube Community
    Edition needs a live Java/Docker server, which doesn't fit this
    tool's single-CLI-invocation architecture. Python: radon's
    Maintainability Index via its own Python API directly (not a
    subprocess -- verified installing and running clean under this
    project's own Python 3.14 before adding it as a real, pinned
    dependency, `>=6.0,<7.0`; a floor+ceiling rather than mutmut's exact
    pin since a stable float-returning API isn't exposed to the
    parsed-CLI-text-output version-drift risk that justified that
    stricter pin). Checked a currently-maintained JS/TS alternative before
    writing anything (last real release matters after tonight's #33
    version-pinning audit): none found -- `wily` (last released
    2026-04-26, more recently than radon itself) turned out to be a
    git-history complexity-*trend* tool built on top of complexity
    engines like radon, not a direct MI-for-this-run tool, so it isn't a
    real substitute; scoped honestly to Python-only rather than adding an
    unverified JS tool. Two real findings from actually running it, not
    just inspecting the code: (a) `def add(a, b): return a + b` scores
    88.6, not the 100.0 a naive guess would assume -- radon's Halstead-
    Volume term is sensitive even to trivial code, so tests assert the
    real observed number, not a rounded guess: (b) the original
    `if not files: return skip("no Python files found")` branch is
    *unreachable* dead code, caught by a failing test: `detect_repo_language`
    and `_python_files` walk the identical `repo.rglob()` with the
    identical `EXCLUDE_DIR_PARTS` filter, so `lang == "python"` (already
    required to reach that line) can only be true when at least one
    non-excluded `.py` file exists -- removed rather than left as an
    illusion of handling a case that cannot occur. Dogfooded on this
    repo's own 62 Python files: mean MI 56.8 (grade A), correctly flags
    `synthesis/deep_reports.py` (15.2) as the single worst-scoring file --
    a genuinely plausible answer given that module's own job (assembling
    every category's report section).
38. **No resilience for a partial pipeline failure.** Raised in the same
    security-grading pass as #33/#28: tonight's own `duplication` timeout
    required noticing, diagnosing, and manually re-invoking just that one
    module three times over -- something only a person watching could do.
    Added `analyze --retry-failed`: reads the existing `run_log.json` in
    `--out`, re-runs only the modules with `status == "error"` (ignores
    `--modules`/`--skip-slow`, since the whole point is "just the ones
    that failed"), and merges the result back in -- every other module's
    prior recorded outcome is left untouched, not silently dropped or
    forced to re-run. Verified with a real, deterministic, fast-failing
    module (`pdf` without `deep_reports` having run first) rather than
    needing a slow/subprocess-heavy one just to have something fail on
    demand.
39. **`testquality.py`'s own module docstring claimed a measurement it
    never took.** It said "Coverage is collected where the runner supports
    it out of the box" -- `TestRunResult` (the dataclass every row of
    `testquality_runs.csv` is built from) has no coverage field, and
    nothing in the module ever passes `--cov`, `--coverage`, or
    `-coverprofile` to any runner. Same failure class as #21 (a claim
    about this module's output not backed by the code that produces it),
    just on the docstring side instead of a downstream JSON-key read. No
    coverage artifact (`coverage.xml` / lcov / a Go cover profile) is
    written by any collector today -- fixed here by correcting the
    docstring, not by building the feature: collecting coverage across
    three different runners, adding CSV columns, and updating every
    consumer (`synthesize.py`, `deep_reports.py`, `exec_deck.py`,
    `trends.py`) is a real feature with its own published-CSV-shape
    sign-off (AGENTS.md §10), not a one-line correction.
40. **`e2e_quality.py` extended with 6 more static config-presence signals**,
    per this doc's own item #34 backlog note: visual-regression tooling
    (`@percy/playwright`/`chromatic`/`toHaveScreenshot`), flake-retry config
    (a `retries:` key), sharding config (`shard:` key or a `--shard` CI
    flag), a11y-in-e2e (`@axe-core/playwright`/`axe-playwright-python` --
    the one signal crossing this module's stated JS/TS-only scope, since
    the Python binding is the realistic way a11y checks reach an
    otherwise-JS/TS E2E suite), trace/video-on-failure config, and
    Pact-based network-mock contract-fidelity presence. All additive to
    `E2EResult` (5 -> 11 fields, none removed/renamed); the early-return on
    "no E2E framework detected" was removed so these signals are computed
    even when no full E2E suite exists (a repo can carry a Pact dependency
    without one). Same zero-subprocess profile as the original module.
