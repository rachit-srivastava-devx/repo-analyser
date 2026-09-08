# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Every entry names the real
reason for the change, not just what changed — recurring mistakes get a rule/ADR, not just a fix
(see `docs/adr/`).

## Unreleased

- **Added `interrogate>=1.5` as a base dependency**: `doc_quality/`'s Python doc-comment-coverage
  measurement (`doc_comment_python.py`) shells out to it, but it was never registered in
  `pyproject.toml`, so a fresh `pip install -e ".[dev]"` per README's own documented setup never
  installed it — the collector's headline Python signal silently degraded to
  `skip_reason: "interrogate not on PATH"` for every repo, on every clean clone, forever. Caught by
  independent verification of the `doc_quality` merge below; fixed by registering it the same way
  `radon`/`vulture` already are (floor-pinned, parsed-text-output caveat documented inline).
- **Added `doc_quality/` collector**: doc-comment coverage (Python via `interrogate`, JS via a
  weaker JSDoc presence-only signal, Go/Rust get an honest `skip_reason` — no keyless tool yet) and
  changelog discipline (presence, last-entry-date, git-tag-comparison staleness). Explicitly v1-
  scoped to these two signals only; doc-freshness-via-content-matching is out of scope, documented
  not silently dropped. Restructured from a 291-line flat file into a package per `AGENTS.md` §4.
  Independently verified in a fresh worktree+venv: 1249 passed/5 skipped, ruff/mypy clean,
  selfcheck 0 FAIL/0 warn, interrogate's coverage math cross-checked against the raw CLI directly
  and by hand-count, changelog staleness verified against real git tags.
- **Added `observability/` collector**: structured-logging/metrics/tracing/Kubernetes-probe
  detection. Restructured from a 343-line flat file into a package per `AGENTS.md` §4.
  Independently verified in a fresh worktree+venv: 1199 passed/10 skipped, ruff/mypy clean,
  selfcheck 0 FAIL/0 warn, adversarial fixtures (comment-only probe-name decoy, binary/non-UTF8
  garbage in config files, 2000-file stress) all handled correctly. CLI-wiring left undone per
  `AGENTS.md` §9 (tracked as a follow-up, not a merge blocker, consistent with every other
  collector merged tonight).
- **Extended `testquality.py`**: test-pyramid shape (unit/integration/e2e/unclassified bucketing),
  fuzz/property-test presence (hypothesis/fast-check/Go native fuzz), snapshot-test-overuse proxy
  (file count + git-log churn). All nine new columns additive. Independently verified in a fresh
  worktree+venv: 1030 passed/10 skipped, ruff/mypy clean, selfcheck clean. **Known follow-up**: the
  file is now 583 lines, well over `AGENTS.md` §4's ~80-line guidance for a single collector file —
  should be restructured into a package (mirroring `notebook_quality/`'s shape) in a future pass.
- **Extended `ci_gates.py`**: pre-commit-hook presence (`.pre-commit-config.yaml`, `.husky/`,
  `package.json` hook keys) and lockfile discipline (presence + whether CI actually enforces it via
  `npm ci`/`poetry check`/`cargo --locked`/`go mod verify`, deliberately excluding plain `npm
  install` since it silently rewrites a drifted lockfile instead of failing). Independently
  verified in a fresh worktree+venv: 1033 passed/10 skipped, ruff/mypy clean, selfcheck clean,
  false-positive resistance confirmed for tool names mentioned only in shell comments.
- **Added `notebook_quality/` collector**: `.ipynb` hygiene — uncleared cell outputs, suspected
  secrets (narrow AWS/OpenAI-key-shaped regex, an explicitly-documented cheap supplement to
  `security.py`'s gitleaks pass, never a replacement), non-monotonic `execution_count` as an
  out-of-order-execution proxy. Cited in `AGENTS.md` §4 as the package-shape worked example.
  Independently verified in a fresh worktree+venv: 1030 passed/10 skipped, ruff/mypy clean,
  selfcheck clean, `notebooks_unparseable` vs `notebooks_total` accounting confirmed correct so
  "no notebooks" and "notebooks we couldn't read" are never conflated.
- **Added `migration_hygiene/` collector**: Data & Persistence Layer static signals — Django/
  Alembic/paired-SQL migration-reversibility detection, orphaned/duplicate migrations (correctly
  scoped per Django app after a fix — see below), committed SQLite/SQL-dump files across full git
  history (content-signature based, distinct from a migration's own legitimate seed-data INSERTs
  and from `security.py`'s credential scanning), static PII-shaped column-name inventory. Live DB/
  execution-requiring criteria (schema drift, connection pooling, query-plan regression, RLS,
  encryption-at-rest, backup/restore) explicitly out of scope, documented not stubbed, no sign-off
  available. Independently verified twice: first pass found a real mainline bug (duplicate-
  migration check wasn't scoped per Django app, so any 2+-app repo — the normal case — got bogus
  false positives) plus a file-size cap overage; both fixed and re-verified clean (1063 passed/10
  skipped, ruff/mypy/selfcheck clean).
- **Added `api_contract/` collector**: API/schema contract-discipline detection — OpenAPI/GraphQL/
  Protobuf spec presence, CI breaking-change-tool detection (`oasdiff`/`graphql-inspector`/`buf
  breaking`/etc.), contract-test tooling presence, deprecation-marker-vs-sunset-date counts.
  Deliberately static-detection-only (matches `ci_gates.py`'s presence-of-practice precedent, no
  new external tool dependency added). Independently verified in a fresh worktree+venv: 1008
  passed/5 skipped, ruff/mypy clean, package itself 99% coverage. **Known follow-up**: CI-tool-
  mention false-positive protection is narrower than its own docstring's example suggests for
  `graphql-inspector`/`openapi-diff`/`swagger-diff`/`buf breaking` (name/phrase-only, no
  invocation-shape gating unlike the well-protected `oasdiff` case); also `docs/METHODOLOGY.md`
  miscounts "six" known tools where `patterns.py` defines five.
- **Merged recovered `pr_review/` module + `write_csv()` hardening**: merge-base resolution, ref
  verification, numstat/name-status diff parsing, added-line-range extraction, GitHub Actions
  event parsing, hunk assembly — recovered from broken, abandoned uncommitted work found at a
  session start, fixed (a real regression in `is_git_repo`/`discover_repos` that had undone an
  already-merged worktree-support fix was restored), and independently verified before merging.
  `write_csv()` now requires an explicit `fieldnames` argument instead of silently deriving an
  empty header from an empty `rows` list — every existing call site updated.
- **`spdx_match.py`'s Apache-2.0/MPL-2.0 false-positive: three independent redesign attempts, all
  rejected on re-verification.** Order-only phrase matching, then section-splitting on structural
  separators, then tightest-window span comparison across signatures — each closed the specific
  counter-example that sank the previous attempt, and each was independently found to still
  misclassify on a different, realistic document shape (a blank-line-separated NOTICE file; a
  BSD-2/BSD-3-with-unrelated-trademark-clause document). Left unmerged. This needs a genuinely
  different approach (e.g. real canonical-license-template similarity matching), not another
  phrase-heuristic patch — tracked in `docs/HANDOFF.md` as a real, hard, open problem.
- **Added `flag_debt/` collector**: feature-flag debt detection — stale/orphaned feature flags via
  SDK usage scanning, `is_enabled()` call-site extraction, and `flags.json`/`.yaml` definition
  cross-referencing (answers polyrepo.md's and microservices.md's feature-flag-SDK-presence rows).
  Merge commit `68a1206`. Independently verified in a fresh worktree+venv: 48 scoped + 703
  full-suite tests, ruff/mypy clean, `selfcheck.sh` 0 FAIL/0 warn, plus adversarial testing
  (malicious YAML RCE payload blocked via `safe_load`, symlink loop handled, SIGKILL mid-scan left
  no partial-write corruption, 5000-file repo in 0.18s, idempotent re-runs byte-identical).
  CLI-wiring left undone per `AGENTS.md` §9 (tracked as a follow-up, not a merge blocker).
- **Added `license_compliance/` collector**: static LICENSE-file SPDX matching and manifest
  license-field cross-check (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.), dispatched by
  detected language. Merge commit `4252f6e`. Fixed a real false-negative in `spdx_match.py`
  (`a237d69`): BSD-3-Clause's signature phrases are matched as a literal, whitespace-sensitive
  substring, so hard-wrapped real-world LICENSE text (prose wrapped at ~70-80 columns) was
  misclassifying as `BSD-2-Clause` or `unknown`; fix collapses whitespace runs before matching.
  Independently verified in a fresh worktree with a from-scratch venv: 49 scoped + 608 full-suite
  tests, ruff/mypy clean; the fix was independently reconstructed against a different LICENSE
  wrap point than the builder's own fixture. **Known follow-up, not a blocker**: signature matching
  is unordered (`all(sig in text)`), which can false-positive Apache-2.0 vs. MPL-2.0 when a text
  contains both licenses' "Version 2.0" phrase — needs an ordered/contiguous match, tracked in
  `docs/ROADMAP.md`.
- **Added `codeowners_health.py`**: CODEOWNERS coverage/accuracy (monorepo.md, polyrepo.md).
  Glob-matches `CODEOWNERS` rules against the tracked file tree for coverage %; a "team no longer
  exists" staleness check needs the GitHub org API and is named as out of scope, not faked.
- **Added `dead_code.py`**: Python dead-code detection via `vulture` (new base dependency, see
  below) and a JS/TS unreferenced-export heuristic. `dead_code_items_python` /
  `unreferenced_export_count_js` are `None` when not applicable (no files of that language, or
  vulture unavailable) and an `int` — including a genuine `0` — once the check actually ran, so a
  `0` is never ambiguous with "didn't check."
- **Extended `inventory.py`**: changelog-presence/staleness detection and a repo staleness band
  (fresh/aging/stale), read by `per_repo_digest.py`.
- **Added `vulture>=2.16`** as a base dependency (`dead_code.py`'s Python path). Floor-pinned, not
  exact — unlike `mutmut`'s exact pin below, vulture's parsed-stdout format has no documented
  history of breaking changes yet; re-verify `vulture_runner.py`'s regex against real output before
  ever bumping past a major version.
- **`scripts/setup.sh` is now a real one-command setup**, not just a jar fetch. It now also
  creates/updates `.venv`, runs `pip install -e ".[dev]"`, and installs the external scanners
  (gitleaks, semgrep, jscpd, osv-scanner, trivy) via brew/npm when missing — checked-only (never
  auto-installed) for Java/Node/Go, since those are language runtimes, not single CLIs. A missing
  external scanner is reported but doesn't fail the script, mirroring the modules' own graceful
  `skipped_reason` degradation — this also keeps `ci.yml`'s existing use of this script (on a
  Homebrew-less `ubuntu-latest` runner) working unchanged.
- **README restructured for scannability**: Quick start moved to the top; long prose (Requirements,
  Security model, Operational cost) condensed to a few bullets with the full detail preserved
  behind `<details>` rather than deleted. Fixed a stale `chronicle/collectors/mutation.py` path
  left over from the 0.2.0 restructure below, and a stale `-chronicle-report.pdf` filename in
  `docs/ARCHITECTURE.md`'s diagram.

## 0.2.0 — rename, restructure, and self-hardening

- **Renamed** `chronicle-analyzer` / `chronicle` package → `repo-analyser` / `repo_analyser`, local
  folder and PyPI-style project name to match. The tool stopped being specific to the
  `chronicle_button` engagement it was modeled on well before this release; the name had not
  caught up. `CHRONICLE_NODE_BIN` env var → `REPO_ANALYSER_NODE_BIN`;
  `CHRONICLE-ADR-001` → `docs/adr/0001-fail-loud-not-silent.md`.
- **Restructured** the flat 25-file `chronicle/` package into `src/repo_analyser/{core,collectors,
  graph,synthesis,reporting}/`, split by dependency direction, not alphabetically. See
  `docs/adr/0002-src-layout-package-split.md` for why and `docs/ARCHITECTURE.md` for the map.
- **Packaged properly**: added `pyproject.toml` (`pip install -e ".[dev]"`, console-script
  `repo-analyser`, `python3 -m repo_analyser` both work); dropped `requirements.txt` as a second,
  driftable source of truth for dependencies.
- **Added a real test suite** (`tests/`, mirroring the source layout) where there was none — see
  "Known issues" in `docs/METHODOLOGY.md` for why that gap mattered: this is a tool whose entire
  premise is "tests that pass are not the same as a feature that works," and it shipped a year
  with zero tests of its own.
- **Added CI** (`.github/workflows/ci.yml`): lint, typecheck, test+coverage on every push/PR. The
  #1 finding this tool produced against its first real target (posx) was "25/26 repos have
  deploy-only CI, nothing blocks a bad merge" — this repo had exactly that gap until this release.
- **Wired Python mutation testing** (`mutmut`) into `collectors/mutation.py`, previously
  JS/TS-only (Stryker). Used to mutation-test this tool's own `ontology.py` classifier as part of
  self-verification — see `docs/METHODOLOGY.md`.
- Added `docs/adr/` (architecture decision log) and `docs/ARCHITECTURE.md` (package map), adapted
  from an L8/principal-engineer operating-contract pattern into `AGENTS.md` — see that file's
  history note.
- **Replaced hand-rolled parsing/formatting with stable libraries** where one already existed:
  `testquality.py`'s Python path now reads pytest's own `--junit-xml` structured output instead of
  three regexes scraping human-readable text (one of which existed only to patch a miscount the
  other two caused); `deep_reports.py`/`report.py`'s duplicated markdown-table builders were
  replaced with `tabulate`, gaining pipe-character escaping neither had. See
  `docs/METHODOLOGY.md` #19–20.
- Fixed a real, previously-uncaught bug: `report.py`'s "Test quality" section read a JSON key
  testquality.py never writes, so REPORT.md's failing-test count has silently read 0 on every run
  since that line was written. See `docs/METHODOLOGY.md` #21.
- **Added `supply_chain.py`** (Trivy): IaC/Dockerfile misconfiguration scanning and CycloneDX SBOM
  generation. Deliberately excludes Trivy's own CVE-scanning mode — `deps_audit.py` already owns
  known-CVE auditing via osv-scanner against the same lockfiles, so running both would duplicate
  the same finding set under two tool names rather than add new signal.

## 0.1.0 — initial release (as `chronicle-analyzer`)

Multi-dimensional, reproducible analysis for a git repo or portfolio: git-history mining, defect
escape rate (SZZ), dependency graphs, duplication (block-level and byte-exact), security scanning,
real executed test-quality checks, code-quality linting, dependency-staleness/CVE auditing, a
cross-repo knowledge graph, and doctrine-styled PDF reports — 18 modules, all wired to real
open-source tools. First run against a 26-repo e-commerce portfolio (`posx`); see
`docs/METHODOLOGY.md` for the full module list and the bugs found while building each one.
