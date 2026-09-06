# Roadmap

Forward-looking work, as distinct from `docs/METHODOLOGY.md` (a log of bugs already found and
fixed) and `CHANGELOG.md` (a log of what shipped). Not a commitment or a schedule — a backlog.

## Checklist-by-repo-type build-out (started 2026-09-06)

Multi-day goal: implement `docs/checklist-by-repo-type/` (21 repo-type checklists + 2 cross-cutting
= 508 criteria) so this tool answers defects at three scopes — one PR, one repo, the whole org
portfolio. This section is the living backlog; move a line to `CHANGELOG.md` once it ships, don't
leave it duplicated in both places.

Gap analysis against the 20 collectors listed in `README.md`'s module table, done 2026-09-06:
circular-dep detection, dependency staleness, bus factor, SAST/SCA/secrets/SBOM, duplication, CCN,
mutation, and defect-escape rate are **already covered** (`depgraph`, `deps_audit`, `inventory`,
`security`, `deps_audit`/`supply_chain`, `duplication`/`exact_duplicates`, `complexity`, `mutation`,
`escape` respectively) — do not rebuild these. Everything below is a genuine gap.

Deliberately **out of v1 scope, stated rather than silently skipped**: any criterion needing a live
running system this tool has no access to from a git clone alone — production DB connections, a
deployed app to DAST-scan, Prometheus/Grafana instances, load-testing infra, GitHub Actions'
own flake-history API. Each such collector should report an explicit `skipped_reason` naming this,
not silently omit the criterion.

**Consolidated CLI-wiring pass, not yet done**: per AGENTS.md §9's policy (a new collector merges
unwired; wiring is a tracked follow-up, not a merge gate), `repo_type.py`, `codeowners_health.py`,
and `dead_code.py` are merged to `dev` but still absent from `cli.py`'s `MODULES`/`run_module` and
README's module table; `license_compliance.py`/`flag_debt.py` will join this list once their own
fixes land (see gap-analysis backlog below). Do this as one batch, one PR, once the current fix
round lands — not piecemeal per collector, to avoid N agents colliding on the same shared files.

### New collectors (each: read AGENTS.md + the nearest shape-alike collector in full before writing;
one new file + `tests/collectors/test_<name>.py`; do **not** touch `cli.py`, `README.md`, or
`synthesis/per_repo_digest.py` — wired in a separate consolidated pass once all land, to avoid N
agents colliding on the same shared files)

- **`repo_type.py`** — implements `docs/checklist-by-repo-type/detecting-repo-type.md`'s full signal
  table (15 original + 13 newer-archetype signals), filesystem/git/manifest-parsing only, no
  external tool. Two independent axes: `primary_type` (single_repo/monorepo/polyrepo/microservices/
  meta_repo — mutually exclusive, first-matching-signal-wins per the doc's own ordering, default
  `single_repo` when nothing else matches) and `content_types` (zero or more of: library_package,
  infra_gitops, docs_repo, developer_tools, qa_testing_infrastructure, ml_data_science,
  rag_vector_store, ai_knowledge_base, agent_skills, smart_contract, mobile_app, design_system,
  embedded_firmware, data_pipeline_etl, browser_extension, game_engine_or_multiagent — a repo can
  match several). Columns: `repo, primary_type, content_types (;-joined), signals_matched (;-joined,
  for traceability — never assert a type with zero recorded evidence), detection_notes`. No
  `skipped_reason` — this always produces an answer; zero content-type matches is a valid, common
  result, not an error.

- **Extend `dead_code.py` (shipped Python+JS/TS, see CHANGELOG) with Go** — `staticcheck`'s U1000
  check (already a `lint_quality.py` dependency — reuse its invocation for this subset rather than
  a second subprocess call). Only the Go path remains; don't rebuild Python/JS.

- **`db_hygiene.py`** — committed database file/dump hygiene (checklist calls this out as "a
  distinct leak vector from credential-pattern secrets scanning" — separate from `security.py`).
  Pure git, no external tool: walk full history (not just current tree) for blobs whose path
  matches `{.sqlite,.sqlite3,.db,.mdb,.sql,.dump,.bak}` and whose size exceeds 10KB (small
  schema-only `.sql` migrations are expected noise, not the finding). Columns: `repo, path,
  extension, size_bytes, first_commit_sha, first_commit_date, still_in_working_tree`. Zero rows is
  a normal, common, non-error result.

- **`observability.py`** — mirrors `performance.py`'s exact shape (two independent signals:
  dependency-manifest presence + config/CI grep, `skip_reason` when nothing found at all — read
  `performance.py` in full as the template). Detects structured-logging (`winston`/`pino`/
  `@opentelemetry/api` JS, `structlog`/`opentelemetry-api` Python, `go.opentelemetry.io/otel`/
  `zerolog` Go), metrics-library presence (`prom-client`/`prometheus_client`/
  `client_golang`), and k8s health-probe config (`livenessProbe`/`readinessProbe` keys under a
  `k8s/`/`deploy/`/`charts/`-shaped dir, or `Chart.yaml`). Columns: `repo, has_structured_logging,
  logging_lib, has_metrics_lib, metrics_lib, has_tracing, tracing_lib, has_k8s_health_probes,
  skip_reason`.

- **`api_contract.py`** — mirrors `performance.py`'s shape again (duplicate its small
  `_load_workflow_docs`/`_step_texts` helpers locally rather than reaching into `performance.py` —
  don't touch that file; promoting the shared helper to `core/util.py` is a separate later backlog
  item once 3+ collectors want it, not earned yet at 2). Detects API schema presence (`openapi.yaml`/
  `.json`, `swagger.yaml`, `schema.graphql`/`*.graphqls`, `*.proto`) and whether a breaking-change
  tool is wired into CI (`oasdiff`, `graphql-inspector`, `buf breaking`, `api-extractor`,
  `cargo-semver-checks`, `apidiff` in workflow step text) plus `.changeset/` dir presence (JS
  semver-bump discipline, weak signal). Columns: `repo, has_schema, schema_kind
  (openapi|graphql|protobuf|none), has_breaking_change_check, breaking_check_tool, has_changesets,
  skip_reason`.

- **`doc_quality.py`** — v1 scope is doc-comment coverage + changelog discipline ONLY. (Doc
  freshness-via-content-matching — diffing a doc's last-edit date against the source it describes —
  is explicitly deferred: too speculative to build reliably in v1, not silently dropped.)
  Doc-comment coverage: Python via `interrogate` (check its real CLI output mode via `--help`, don't
  guess a flag); JS/TS via `eslint-plugin-jsdoc` dependency + config presence (weaker, presence-only
  signal — consistent with this tool's existing precedent for where live measurement isn't
  practical); Go/Rust → `skipped_reason` (no keyless scriptable coverage-% tool for these yet — name
  the gap, don't fake a zero). Changelog discipline: `CHANGELOG.md`/`HISTORY.md` presence + whether
  its newest dated/versioned entry is older than the repo's newest git tag (pure git+file, no
  external tool). Columns: `repo, doc_comment_coverage_pct, doc_comment_tool, has_changelog,
  changelog_last_entry_date, changelog_stale_vs_latest_tag, skip_reason`.

- **`meta_repo_health.py`** — consolidates 5 related `meta-repo.md` criteria (manifest
  drift/staleness, pinned-commit correctness, submodule/subtree lag, broken/dangling refs, manifest
  schema validation) into one collector rather than 5. Detects manifest kind (`.gitmodules` /
  `manifest.xml` repo-tool / `west.yml` Zephyr), then per declared sub-repo: is it pinned to an
  exact commit, how far behind its remote HEAD (needs `git ls-remote` — the one network call in
  this batch; short timeout via `core.util.run`, a network failure is `ToolExecutionError`, never a
  false "in sync"), and whether the URL still resolves at all. Columns: `repo, manifest_kind,
  submodules_total, submodules_pinned_to_commit, submodules_behind_upstream, broken_refs,
  skip_reason`.

- **`notebook_quality.py`** — `ml-data-science.md`'s notebook hygiene. Per `.ipynb` file: outputs
  cleared before commit (any cell with a non-empty `outputs` array is flagged), a narrow local
  regex check for obvious secret patterns in cell source (a cheap redundant net only —
  `security.py`'s gitleaks already scans the whole tree including notebooks-as-text, this is NOT a
  replacement for that), and a crude re-executability proxy (non-monotonic `execution_count`
  sequence across cells suggests cells were run out of order, not top-to-bottom before commit).
  Columns: `repo, notebooks_total, notebooks_with_uncleared_outputs,
  notebooks_with_suspected_secrets, notebooks_nonlinear_execution, skip_reason`.

- **`tooling_drift.py`** — monorepo-scoped (most meaningful once `repo_type.py` flags
  `primary_type=monorepo`, but doesn't have to gate on it). Walks a repo tree for MULTIPLE
  manifests (not just one at repo root, unlike most collectors here — genuinely different
  traversal shape, name this explicitly in the module docstring) and flags the same dependency
  pinned to different versions across sibling packages, plus lint/format config divergence
  (`.eslintrc*`, `pyproject.toml`'s `[tool.ruff]`, `.golangci.yml`) between them. Columns: `repo,
  config_kind, packages_compared, packages_with_drift, drift_detail (;-joined pkg@version pairs),
  skip_reason`.

- **`agent_skill_quality.py`** — for repos `repo_type.py` flags `agent_skills` content-type.
  v1 scope deliberately narrow: schema presence + structural validity (does `SKILL.md`
  frontmatter / an MCP tool-definition JSON parse at all, with the expected top-level keys) and
  description-completeness (tools with vs. without a description field — a weak proxy the
  checklist itself calls "triggering-accuracy," not a real eval). Explicitly OUT of v1: any
  semantic privilege-scope or prompt-injection analysis — those need live LLM calls, a fundamentally
  different (evaluation, not static-analysis) category, named as a gap not attempted. Columns:
  `repo, tool_defs_found, tool_defs_valid_schema, tool_defs_with_description, skip_reason`.

- **`microservices_topology.py`** — scoped down from the research pass's ~12 separate proposals
  (a real speculative-abstraction risk, see the microservices.md gap-analysis note above) to the
  highest value-for-effort subset for v1: from docker-compose/k8s manifests, (a) service count +ạ
  dependency-cycle check via `depends_on`/service-reference edges (reuse `networkx`, already a
  dependency via `knowledge_graph.py`), (b) service-mesh/mTLS presence (Istio/Linkerd CRD or
  sidecar-injection annotation grep), (c) default-deny network-policy presence, (d) canary/
  progressive-rollout config presence (Flagger/Argo Rollouts CRD), (e) resilience-library
  dependency presence by name per language (presence only, never correctness — timeout/retry
  code-level correctness needs AST-level judgment, explicitly deferred past v1). Columns: `repo,
  service_count, has_dependency_cycle, cycle_detail, has_service_mesh, mesh_kind,
  has_network_policy_default_deny, has_canary_rollout_config, resilience_libs_detected (;-joined),
  skip_reason`.

### Extensions to existing collectors (each: read the full existing file first — this *is* the
reuse check AGENTS.md §2.2 requires — then add columns preserving every existing column; one file
touched per task, no two tasks share a file)

- **`e2e_quality.py`**: add visual-regression config detection (`toHaveScreenshot`/
  `@percy/playwright`/`chromatic`), flake-retry config (`retries:` key), sharding config (`shard:`
  key or `--shard` in CI text), a11y-in-e2e (`@axe-core/playwright`/`axe-playwright-python` dep),
  trace/video-on-failure config (`trace:`/`video:` keys present at all — v1 doesn't judge the value),
  network-mock contract fidelity (`@pact-foundation/pact` dep). All presence/config-grep, no new
  subprocess tool — matches this file's existing shape.
- **`testquality.py`**: add test-pyramid shape (split `core.lang.TEST_FILE_RE` matches by
  unit/integration/e2e using a directory-name heuristic — document it as a heuristic, not ground
  truth), fuzz/property-based test presence (`hypothesis` Python dep, `fast-check` JS dep, `func
  Fuzz` Go convention — presence-only), snapshot-test overuse (`.snap` file count + `git log
  --follow --oneline -- '*.snap' | wc -l` churn proxy).
- **`deps_audit.py`**: add license-compliance column (JS: `license-checker` if available; Python:
  `pip-licenses` — only inside the target's own venv, same precondition `testquality.py` already
  documents, `skip_reason` otherwise; Go: `go-licenses` if available) flagging anything outside
  {MIT, Apache-2.0, BSD-2/3-Clause, ISC} as `license_violations`. Also verify staleness
  (`npm outdated`) is JS-only today; if so, add the same staleness shape for Python (`pip list
  --outdated --format=json`) and Go (`go list -u -m -json all`).
- **`effort.py`**: add portfolio-wide contribution-inequality (Gini/Lorenz) across *all* repos'
  authors combined (not per-repo — `inventory.py`'s `_gini` already does per-repo bus-factor; this
  is the same formula applied to one portfolio-wide author→total-commits map — reuse the formula,
  it's already precisely defined in `inventory.py`'s docstring). Onboarding time-to-first-commit is
  explicitly OUT of v1 scope here: git has no "repo access granted" timestamp, so any proxy for it
  would be silently mislabeling a different thing as that metric — name this gap in the module
  rather than faking the measurement.
- **`ci_gates.py`**: add pre-commit hook presence (`.pre-commit-config.yaml`, `.husky/`, or
  `pre-commit`/`lint-staged` in package.json) and lockfile discipline (lockfile presence
  {`package-lock.json`,`pnpm-lock.yaml`,`yarn.lock`,`poetry.lock`,`Pipfile.lock`,`Cargo.lock`,
  `go.sum`} plus whether CI verifies it — `npm ci` not `npm install`, `poetry check`, `cargo
  build --locked`/`test --locked`, `go mod verify` in workflow step text).
- **`lint_quality.py`**: add lint-suppression density — count `# noqa`/`# type: ignore` (Python),
  `eslint-disable` (JS/TS), `//nolint` (Go) per KLOC across tracked source, excluding
  `core.lang.EXCLUDE_DIR_PARTS`.

### Net-new mode: per-PR diff-scoped review (`docs/checklist-by-repo-type/pr-review.md`, 28
criteria) — design pass complete (2026-09-06), implementation proceeding wave-by-wave. This is the
single most-requested capability behind this whole build-out ("find defects per PR").

**Registry decision**: new sibling subpackage `src/repo_analyser/pr_review/`, not a `collectors/`
extension or a `--diff` flag on `analyze`. Reasoning: `collectors/`'s convention is
`run_x(repos: list[Path], out_dir: Path)` — a *portfolio* signature; PR mode is one repo × one
commit range, a genuinely different axis (AGENTS.md §4's bar for a new shape). New signature for
this subpackage: `run_x(repo: Path, ctx: PrContext, out_dir: Path) -> Path`. New CLI subcommand
`repo-analyser review-pr <repo> [--base REF] [--head REF]`, not a flag on `analyze` — the two
modes share zero module names, and a flag would force 4 existing `tests/test_cli.py` cases to grow
a field they don't need. `analyze`, `MODULES`, `run_module` stay untouched by this whole effort.

**The one finding that would have silently corrupted every PR-size/diff number**: use
`git merge-base <base> <head>` once, then every module diffs `merge_base..head` (three-dot), never
`base..head` (two-dot) — GitHub's own "Files changed" view is three-dot. Two-dot attributes every
commit landed on the base branch since the fork point to this PR, the single most likely source of
a wrong PR-size/file-list number. Record `merge_base_sha` and put it on every PR CSV row alongside
`base_sha`/`head_sha` — same non-negotiable as every existing CSV's `repo` column.

**Mechanism per criterion — the sortable rule is the shape of the property, not "how hard it
looks"**: M1 native-baseline (a tool already answers "what's new since X" — `semgrep
--baseline-commit`, `gitleaks git --log-opts`, both verified working against this repo's own
history); M2 two-point differential (compute `f` at both refs, diff the sets — osv-scanner
lockfile diff, API-surface diff); M3 diff-intrinsic (a fact about the diff itself needing no
base-vs-head measurement — PR size, CODEOWNERS, stale-base); M4 filter-over-head (state of changed
files AT HEAD, diff only selects rows — complexity/duplication of touched files). **M4 was the
naive first instinct (filter existing collectors' output to changed files) and it's wrong for
anything M1/M2 already covers**: filtering `security_semgrep.csv` to touched files answers "which
pre-existing findings live in touched files," not "which findings this PR introduced" — a
proxy-for-the-property bug (AGENTS.md §6) baked into the CSV before anyone even runs it. Verified
this is also NOT the cheap option — `semgrep --baseline-commit` on this repo's own 3-file diff
scanned exactly 3 files; running the whole-repo `security` module to discard 99% of rows would be
both slower and wrong.

**Verified tool-flag corrections to the checklist itself** (real commands run against this repo,
not guessed): `Gitleaks protect --staged` — **`protect` subcommand no longer exists** in gitleaks
8.30.1; correct lever is `gitleaks git --log-opts "<merge_base>..<head>"`. `OSV-Scanner (lockfile
diff)` — **no such flag**; `scan source -L <path>` takes one file, diffing is this tool's own job
(run it at both refs, set-difference the results) — but `scan source --licenses <allowlist>` *does*
exist and directly serves the license-gate criterion. `diff-cover` — installed and real, but
**blocked**: no collector produces a coverage artifact at all (`testquality.py`'s own docstring
claims coverage is collected "where the runner supports it" — verified false, zero
`--cov`/`--coverage`/lcov anywhere in that file; flagged as its own small fix, see below, not
silently left as a false claim).

**Base/head resolution** (recorded in `pr_review_context.json`'s `resolved_via` field, in this
order): explicit `--base`/`--head` flags (each validated via `git rev-parse --verify`, never
interpolated into a shell string — refs from a fork PR are attacker-controlled) → GitHub Actions
`GITHUB_EVENT_PATH` JSON's `pull_request.base.sha`/`.head.sha` when `GITHUB_EVENT_NAME ==
"pull_request"` (not `GITHUB_BASE_REF`/`HEAD_REF` — those are branch names, meaningless on the
synthetic merge-commit checkout a `pull_request` event actually gives you) → error, never guess
(`HEAD` vs `origin/main` on a stale checkout silently produces a wrong-sized diff).

**28-criteria triage** (9 v1-buildable · 5 split, keyless half only · 6 deferred to v2 · 8
genuinely out of scope — needs a live preview deploy, a paid API, or org infra):

<details>
<summary>Full per-criterion verdict + module assignment</summary>

| # | Criterion | Verdict | Module |
|---|---|---|---|
| 1 | New-code quality gate | split | `changed_file_quality.py` (complexity+dup of changed files, M4); coverage half blocked on the missing-coverage-artifact gap below |
| 2 | PR size vs. reviewability | v1 | `size.py` |
| 3 | Diff-scoped lint annotations | v1 | `lint_diff.py` — scope must read `added_lines`, never `files_touched` |
| 4 | Review-rigor gate | split | `ownership.py` (CODEOWNERS-match keyless half); approval state is out (needs GitHub API) |
| 5 | Diff-aware SAST | v1 | `sast_diff.py`, `semgrep --baseline-commit`, verified |
| 6/22/24 | New-dep CVE/license, CVE-scoped-to-diff, lockfile-diff scan | v1, **one module** (checklist lists the same dimension 3×) | `deps_diff.py` |
| 7 | Diff-scoped secrets scan | v1 | `secrets_diff.py`, `gitleaks git --log-opts`, verified |
| 8 | Authz-sensitive path escalation | v1 | `ownership.py` (same module as #4) |
| 9 | Benchmark regression gate | v2 | needs build+run at both refs — sequence after whole-repo benchmark *execution* (already open in this doc under `performance.py`) |
| 10 | Bundle-size delta | v2 | same cost class as #9; a cheap M3 slice ("budget loosened in this diff") is v1-feasible if picked up early |
| 11 | Web perf budget | out | needs a live preview deploy |
| 12 | Query/latency benchmark delta | out | needs a running app + DB |
| 13 | Affected-project computation | v1 | `affected.py` — tier 1 real tool (`nx`/`turbo`/`bazel`, verify flags via `--help` first) tier 2 keyless fallback (workspace-glob one-hop reverse deps) |
| 14 | Consumer-driven contract gate | out | Pact Broker = org infra |
| 15 | Reverse-dep lookup across polyrepo | v2 | this tool's own portfolio mode (`discover_repos` on a dir) is a uniquely good fit — grep siblings for imports of the changed package |
| 16 | Auto-posted consumer list | out (as posting) | content = #13's output; posting needs a bot token |
| 17 | Public API surface diff | v2/wave 3 | `api_surface_diff.py` — Python (`griffe`)/Go (`apidiff`) only in v1, JS needs a full build; **new tool dep, flag for human sign-off** |
| 18 | OpenAPI/GraphQL breaking-change | v2/wave 3 | `schema_breaking.py`, sequence after `api_contract.py` lands; **new tool dep, flag for human sign-off** |
| 19 | Missing-changeset gate | v1 | folds into `size.py` |
| 20 | Downstream-consumer breakage estimate | out | deps.dev is keyless but a live registry round-trip per package — `deps_audit.py`'s own docstring already documents `npm audit` hanging for exactly this reason |
| 21 | License allowlist on new deps | v1, same module as #6 | `deps_diff.py` + `osv-scanner --licenses`; **allowlist definition must not diverge from the whole-repo `deps_audit.py` license column already planned above — reconcile, don't duplicate** |
| 23 | Supply-chain health score | out | needs a GH token in practice; confirmed `supply_chain.py` is Trivy misconfig+SBOM, not Scorecard — genuine gap, keyed |
| 25 | PR-age staleness gate | split | keyless half is #26; "sat open N days" needs PR metadata, out |
| 26 | Stale-base / conflict-risk | v1 | `base_freshness.py` — `git rev-list --count` + `git merge-tree --write-tree --quiet` (non-destructive conflict probe, verified against git 2.51) |
| 27 | Flexibility-reduction check | v2, explicitly heuristic | ArchUnit/Deptrac are JVM/PHP-only; honest narrow slice = grep added lines for a literal replacing a removed `process.env`/`os.environ` read |
| 28 | Reversibility gate | out | the honest keyless version is a whole-repo signal (does this repo use a flag SDK at all), not a PR one |

</details>

**Build waves** (each brief: read AGENTS.md + nearest shape-alike in full first; one new file + its
own test file; don't touch `cli.py`/`README.md`/`docs/ARCHITECTURE.md`/`per_repo_digest.py` —
wired in one consolidated pass, last):

- **Wave 0 (solo, blocks everything else)**: `pr_review/context.py` (base/head/merge-base
  resolution + provenance) + `pr_review/diff.py` (one `ChangedFile` model: numstat, added-line
  ranges via `--unified=0`, rename detection via `--find-renames`, generated-file detection via
  `.gitattributes`) + `tests/pr_review/conftest.py` with a fixture repo whose base has **diverged**
  from head (a linear fixture can't catch a two-dot/three-dot bug — confirmed on this repo's own
  linear history, both report the same file count, proving nothing). Edge cases: base==head (valid,
  zero rows), a shallow clone where `merge-base` fails (raise naming `fetch-depth: 0` explicitly —
  the single most common real CI failure mode for this), an unparseable `GITHUB_EVENT_PATH`.
- **Wave 1 (parallel once Wave 0 lands)**: `size.py` (#2/#19), `sast_diff.py` (#5),
  `secrets_diff.py` (#7), `base_freshness.py` (#26), `ownership.py` (#4/#8 keyless halves).
- **Wave 2 (parallel once Wave 1 lands)**: `deps_diff.py` (#6/#21/#22/#24), `lint_diff.py` (#3),
  `affected.py` (#13), `changed_file_quality.py` (#1 partial).
- **Wave 3**: `pr_review/report.py` (renders `PR_REVIEW.md`, fixed narrative order — never
  `glob().sort()`, that exact bug already happened twice per AGENTS.md §6); `api_surface_diff.py` /
  `schema_breaking.py` once their new-tool-dependency sign-off happens.
- **Wave 4 (one shared pass, done last, by the orchestrator alone)**: `cli.py` (`PR_MODULES` +
  `cmd_review_pr` + `run_pr_module`, writes `pr_run_log.json` — deliberately NOT `run_log.json`,
  or `analyze --retry-failed` in the same dir would read a PR run's log by accident; default out
  path `analyses/<repo>/pr/<merge_base[:7]>..<head[:7]>/`), `README.md` module table,
  `docs/ARCHITECTURE.md` subpackage-map row, this section moved to `CHANGELOG.md`.

**Flagged, not resolved here (AGENTS.md §8 stop-conditions)**:
1. `api_surface_diff.py`/`schema_breaking.py` add genuinely new external tool dependencies
   (griffe/apidiff/oasdiff/buf) — needs the human sign-off §2.2 already requires for any new tool,
   deferred to Wave 3.
2. The `--licenses` allowlist definition will exist in two places (`deps_diff.py` here, and the
   whole-repo `deps_audit.py` license-compliance column already in progress above) — must be
   reconciled to the same allowlist when both exist, not left to silently diverge.
3. **Found, not yet fixed**: `testquality.py`'s module docstring claims coverage is collected
   "where the runner supports it" — verified false (no `--cov`/`--coverage`/lcov invocation
   anywhere in the file). This blocks criterion 1's coverage half and is a real, if small,
   fail-loud violation in already-shipped code (a docstring asserting a capability that doesn't
   exist) — fix the docstring wording in the same pass that reviews/merges the in-flight
   `testquality.py` extension (don't hand-edit that file while another agent has it checked out).

### Specialized repo-type checklists — gap analysis (2026-09-06)

4 of 5 fan-out research batches back (microservices.md still running as of this write). Format:
`criterion → COVERED(collector, why) | EXTEND(collector, what to add, tool) | NEW(name, tool, what
it measures) | OUT_OF_SCOPE(why)`. **Tool/module names here are unverified proposals from a
read-only research pass** — before anyone implements one, the same rule the build tasks above
already follow applies: check the tool's real `--help`/flags first, don't assume. A `NEW(...)`
entry is a candidate, not a commitment — several plausibly overlap (e.g. multiple "config drift"
or "practice-maturity benchmarking" proposals across files) and should be merged into one collector
per real dimension when picked up, not built once per file that happened to mention it.

<details>
<summary>monorepo.md, meta-repo.md, library-package.md, infra-gitops.md</summary>

**monorepo.md — Build System Health**
- Build graph correctness → OUT_OF_SCOPE(needs live build execution)
- Remote/incremental cache hit rate → OUT_OF_SCOPE(needs cache monitoring infra)
- Cold vs. warm build/test time at scale → OUT_OF_SCOPE(needs build profiling infra)
- Cache correctness (false hits) → OUT_OF_SCOPE(needs build execution)
- Bazel/Nx/Turborepo/Buck2/Pants-specific health → NEW(one auditor per tool: `buildifier`+`bazel query`, `nx graph`, `turbo.json` parsing, `buck query`, `pants tailor` — genuinely 5 different ecosystems, don't force one module)

**monorepo.md — Repo-Scale Infra**
- Source-control scalability, code-intel index at scale → OUT_OF_SCOPE(infra/service monitoring, not source analysis)

**monorepo.md — Dependency Graph Hygiene**
- Circular deps between internal packages → COVERED(depgraph)
- Unintended cross-package coupling, dep-graph depth/fan-out, module boundary violations → EXTEND(depgraph, forbidden-rules + transitive-depth columns, dependency-cruiser/import-linter)
- Orphaned/unused internal packages → NEW(orphaned_packages, knip/vulture/deadcode/cargo-machete — overlaps `dead_code.py` already in progress, fold in rather than duplicate)
- Phantom/undeclared deps → EXTEND(depgraph, depcheck/go mod tidy/deptry)
- Continuous CVE monitoring across all packages → COVERED(deps_audit, one osv-scanner pass already covers the whole portfolio)

**monorepo.md — Ownership & Boundaries**
- CODEOWNERS coverage/path validity → NEW(codeowners_audit, codeowners-validator)
- CODEOWNERS team/user existence, org-wide conformance enforcement → OUT_OF_SCOPE(needs GitHub org API)
- Module/import boundary violations → EXTEND(depgraph, layering rules, dependency-cruiser/import-linter)

**monorepo.md — CI Scaling, Access Control** — almost entirely OUT_OF_SCOPE (needs live CI runner history, GitHub Rulesets/permissions API, cloud billing) except: Visibility-as-build-boundary → NEW(visibility_auditor, bazel/buck query parsing)

**monorepo.md — Versioning, Shared Tooling, Org Toil**
- Ability to release one package independently → COVERED(repo_type.py's monorepo detection + changelog/tag structure, once built)
- Changeset/release-tooling correctness, release-graph drift → OUT_OF_SCOPE(needs a real dry-run publish)
- Lint/tsconfig/dep-version/codegen drift across packages → NEW(tooling_drift_auditor family — config-parsing only, no external tool, matches `repo_type.py`'s filesystem-only precedent; consider ONE collector with multiple drift-dimension columns rather than 4 files)
- Merge-conflict rate/hot files → EXTEND(churn, `git log --diff-filter=U` historical scan)
- PR queue wait, time-to-green, CI cost → OUT_OF_SCOPE(needs GitHub Actions API/billing)

**meta-repo.md** (10/10, mostly buildable pure-git)
- Manifest drift/staleness, pinned-commit correctness, submodule/subtree lag, broken/dangling refs, manifest schema validation → NEW(one `meta_repo_health` collector covering all 4 — same file (`.gitmodules`/manifest.xml/west.yml), same mechanism (`git submodule status`+`git ls-remote`), don't split into 4 files)
- Fresh-clone build reproducibility, cross-repo pin compatibility, automated bump cadence, cross-repo bisectability, round-trip baseline tracking → OUT_OF_SCOPE(needs real build execution, Renovate/Dependabot state, or a live sync tool's own state)

**library-package.md** (17 total)
- Semver discipline/API-surface diffing → NEW(semver_auditor, cargo-semver-checks/api-extractor/apidiff — overlaps `api_contract.py` already in progress, fold in)
- Changelog accuracy vs. actual commits → EXTEND(doc_quality.py once it exists, git-cliff/conventional-commits cross-check)
- Deprecation-policy enforcement → NEW(deprecation_audit, eslint-plugin-deprecation/staticcheck/rustc `#[deprecated]` grep)
- Backward-compat test-suite presence → NEW(compat_test_audit, `.snap`/approval-test-framework presence — overlaps testquality.py's snapshot-overuse extension already in progress, fold in)
- Bundle size/tree-shakeability → NEW(bundle_audit, size-limit/webpack-bundle-analyzer — overlaps performance.py's bundle-budget detection, check before building separately)
- Package manifest correctness → NEW(manifest_audit, publint/are-the-types-wrong/twine/`cargo publish --dry-run`)
- Install-time lifecycle-script risk → NEW(lifecycle_script_audit, lockfile-lint + pre/postinstall grep — genuinely new, matches this tool's own documented `--ignore-scripts` security concern in ARCHITECTURE.md, a natural fit)
- CI hardening of the package's own publish workflow → NEW(publish_ci_hardening, OpenSSF Scorecard/zizmor/actionlint)
- Reproducible builds, peer-dep range correctness → NEW/lower priority
- Published-artifact-vs-source drift, downstream-breakage risk, publish-path 2FA, typosquat monitoring, unpublish policy, multi-registry consistency → OUT_OF_SCOPE(needs registry-side API access, all keyed or org-infra)
- Library CVE monitoring post-publish → COVERED(deps_audit, scheduled reruns already catch this per the recurring-CI-run feature)

**infra-gitops.md** (13 total)
- Policy-as-code compliance → NEW(iac_policy_audit, OPA/Conftest/Kyverno)
- IaC security/misconfig scanning → EXTEND(supply_chain.py, it already runs Trivy — check whether tfsec-equivalent checks are already included before adding Checkov/Terrascan)
- Secret leakage in IaC files → COVERED(security.py, gitleaks already scans full tree/history including `.tf`/`values.yaml`)
- State-file integrity/locking, least-privilege pipeline creds, module/chart version pinning, provider/module CVE monitoring → NEW(static config-parsing collectors, no live cloud access needed for these specific 4)
- Plan/apply review discipline, GitOps reconciliation health, blast-radius analysis, module functional testing, orphaned-resource detection → OUT_OF_SCOPE(needs a live Atlantis/Argo CD/Flux/cloud-provider connection)
</details>

<details>
<summary>polyrepo.md (86 criteria)</summary>

- Clone/duplication detection across fleet → COVERED(duplication.py, portfolio-wide jscpd already)
- Cross-repo dependency graph → COVERED(knowledge_graph)
- Zombie/duplicate repo detection → COVERED(exact_duplicates.py)
- Bus factor, staleness/abandonment per repo → COVERED(inventory.py)
- Release cadence, DORA metrics fleet-wide → COVERED/PARTIAL(inventory.py tags + escape.py + synthesize.py — verify before assuming full DORA coverage, deployment-frequency-from-tags is a proxy not a direct measure)
- SAST/SCA/secrets/license/IaC scanning parity across the fleet → COVERED(security/deps_audit/supply_chain — one portfolio-wide run already covers every repo, "parity" just means reading the existing per-repo rows across the whole CSV, likely a synthesis-layer view not a new collector)
- CCN, duplication %, mutation score per repo → COVERED(complexity/duplication/mutation)
- Static-analysis issue density → COVERED(lint_quality)
- API spec centralization → COVERED(api_contract.py, once built)
- Schema/breaking-change detection → COVERED(api_contract.py presence half; breaking-change execution is the still-open half already noted in its ROADMAP bullet)
- README completeness, ADR discoverability, CODEOWNERS presence, naming-convention consistency, repo-count/growth trend, lockfile enforcement per repo, runtime/language-version matrix across repos, feature-flag SDK presence → NEW(mostly filesystem/config-grep collectors — real candidates, several overlap ci_gates.py's lockfile-discipline extension already in progress; runtime-version-matrix is a natural `inventory.py` or new small collector)
- Hotspot analysis (complexity × churn) fleet-ranked → EXTEND(complexity.py or synthesize.py — this tool likely already has the raw numbers, check whether it's a synthesis-layer ranking rather than a new collector before building)
- Transitive dependency fan-out depth → NEW(transitive_depth, `npm ls`/`pipdeptree`/`go mod graph`)
- Security-debt aging, changelog/release-note staleness → EXTEND(security.py / ci_gates.py respectively)
- Everything else (~45 criteria: shared-library adoption via org API, semver/lockstep coordination via deploy metadata, contract testing via Pact Broker, CI template/branch-protection/permission audits via GitHub API, service-catalog coverage via Backstage, cross-repo PR timing via GitHub API, redundant CI spend via billing API, cross-repo refactor cost via codemod execution) → OUT_OF_SCOPE(needs org-level GitHub/GitLab API access, a paid registry/catalog service, or live deployment infra — this single-clone-at-a-time tool's "portfolio" mode is multiple LOCAL clones, not an org-API integration; a `gh api`-based collector is a plausible FUTURE keyless option for the GitHub-API-shaped subset specifically, worth a dedicated look later, not assumed in scope now)
</details>

<details>
<summary>microservices.md (89 criteria)</summary>

Sharpest split of any batch: this checklist is mostly about a *running* system (service mesh,
live tracing, chaos experiments, cluster metrics) this git-clone-only tool has no access to —
roughly 55 of 89 criteria are OUT_OF_SCOPE for that reason (bounded-context alignment, god-service/
chatty-service smells, cascading-failure/backpressure/idempotency, saga/outbox/CQRS-lag
correctness, four-golden-signals/USE-method/symptom-based alerting, chaos-engineering/game-days/
load-testing coverage, service-mesh live health/traffic/version-skew, cost/right-sizing/
idle-service detection — all need a live cluster, broker, mesh control plane, or metrics backend).

What IS statically buildable (all from k8s manifests / docker-compose / CI YAML / source grep — no
live cluster needed, matching this tool's existing "config presence, not live execution" precedent
from `performance.py`/`e2e_quality.py`): distributed-monolith / shared-database smells, cyclic
service dependencies (docker-compose/k8s parsing + networkx — this repo already depends on
networkx for `knowledge_graph.py`), timeout/retry/circuit-breaker/bulkhead config presence,
distributed-transaction (2PC/XA) and dual-write anti-pattern grep (semgrep custom rules — this tool
already runs semgrep in `security.py`, a custom ruleset is a natural extension there rather than a
new dependency), per-service SLO config presence, consumer-contract-test presence, API-gateway
config, mTLS/cert-management/network-policy/egress-policy config (Istio/Linkerd CRDs, k8s
NetworkPolicy), canary/rollout config (Flagger/Argo Rollouts CRDs), feature-flag SDK presence,
hard-coded-endpoint grep, autoscaling (HPA/VPA/KEDA) config sanity.

**Consolidation note before building any of this**: the research pass proposed ~20 separate
`NEW(...)` module names for the above (`service_topology_audit`, `timeout_config_audit`,
`retry_config_audit`, `resilience_pattern_audit`, `bulkhead_pattern_audit`, `service_mesh_audit`,
`network_policy_audit`, `egress_policy_audit`, `api_gateway_audit`, `canary_rollout_audit`,
`autoscaling_config_audit`, `secrets_management_audit`, `service_authz_audit`, ...) — that's a
speculative-abstraction smell (AGENTS.md §4) more than a real 20-dimension split, since most of
them are "parse the same k8s/docker-compose YAML tree, look for a different key." Whoever picks
this up should design ONE `microservices_topology.py`-style collector reading the manifest tree
once and reporting several columns (resilience-pattern presence, mesh/mTLS config, network-policy
posture, canary/rollout config, autoscaling config), not 12+ separate subprocess-free file walks —
same reasoning as the monorepo tooling-drift consolidation note above. The semgrep-rule-based ones
(2PC/XA usage, dual-write detection, hard-coded endpoints) are a better fit as new custom rules
fed into `security.py`'s existing semgrep invocation than as separate collectors.

Partial overlaps with in-progress work, don't rebuild: distributed tracing coverage → mostly
`observability.py`'s tracing-library detection (trace-CONTEXT-propagation specifically is a real,
narrow addition on top — `traceparent` header grep); schema versioning/backward-compat/N/N-1
rollout compatibility → `api_contract.py`'s schema+breaking-change detection already covers the
static half; event-schema-registry governance is a real, separate extra column on `api_contract.py`
(Apicurio/Karapace config presence) once that file exists; per-service supply-chain provenance and
continuous CVE monitoring → `supply_chain.py` extension (per-image Cosign-signing config, scheduled
scan detection), not a new file; redundant cross-cutting capability duplication across services →
already `duplication.py`'s job at the portfolio level, no new work needed.
</details>

<details>
<summary>docs-repo.md, developer-tools.md, qa-testing-infrastructure.md, ml-data-science.md, rag-vector-store.md, ai-knowledge-base.md, agent-skills.md</summary>

**docs-repo.md**: content freshness (front-matter vs. git log), broken-link detection (lychee/markdown-link-check), doc-to-code drift (CLI `--help` snapshot diffing), style/terminology linting (Vale/alex), doc-build validation (`mkdocs build --strict`), accessibility/alt-text, readability scoring → all NEW, all static/git-only, no live system needed — a real, coherent doc-quality collector family (some of this may fold into `doc_quality.py`'s doc-freshness half, explicitly deferred there — revisit together). Search/discoverability, on-page feedback → OUT_OF_SCOPE(needs a live indexing/widget service).

**developer-tools.md**: CLI `--help`-text snapshot testing, shell-completion-script correctness, plugin/extension API back-compat → NEW, all buildable by invoking the repo's own CLI/build output. Cross-platform coverage, install-method coverage, telemetry opt-out compliance → OUT_OF_SCOPE(needs multi-OS CI execution or live network capture).

**qa-testing-infrastructure.md**: "meta-testing" (does this framework's own logic get mutation-tested) → COVERED(mutation.py already runs against any repo including a test-framework repo itself). Flake-detector accuracy, synthetic-test-data realism → NEW but low-confidence/hard to verify without a labeled ground truth — deprioritize. Cross-team adoption consistency → OUT_OF_SCOPE(needs visibility into other repos' pinned versions).

**ml-data-science.md**: notebook hygiene (cleared outputs, embedded secrets, re-executability) → EXTEND(testquality.py or a small new collector, nbstripout/nbQA/gitleaks-on-notebooks — real, concrete, buildable). Experiment reproducibility, data-schema validation, model-regression testing, data lineage, model-registry versioning, model-card completeness, artifact-storage hygiene → NEW but each assumes a specific ML framework's own metadata files (MLflow/DVC/dbt) being present — presence-only detection is fair game, deep validation is not. Bias/fairness evaluation, GPU/compute cost tracking → OUT_OF_SCOPE(needs live model execution or cloud billing).

**rag-vector-store.md**: chunking-config versioning, PII-scrubbing-before-embedding presence, embedding-model-version pinning → NEW, static/config-detectable. Everything else (retrieval quality, hallucination rate, ACL leakage, cost-per-query, index freshness) → OUT_OF_SCOPE(fundamentally needs a live vector store + running retrieval pipeline — this is the single most "needs a live system" checklist of the batch).

**ai-knowledge-base.md**: front-matter schema validation, content-freshness TTL enforcement, context-window/token-budget discipline (tiktoken counting against these files — cheap, real, buildable), redundancy/conflict detection across files → NEW, several genuinely easy (frontmatter schema, token budget). Retrieval-accuracy testing, access-scope correctness → OUT_OF_SCOPE(needs a live retrieval pipeline or live DB row-level-security connection).

**agent-skills.md**: tool/function-schema validation (JSON Schema/Pydantic/Zod against the repo's own declared schemas), least-privilege capability-scoping audit, tool-signature versioning/breaking-change diff → NEW, static/schema-file analysis, real and buildable. Prompt-injection resistance, tool-call accuracy scoring, replay-determinism testing → OUT_OF_SCOPE or LOW-CONFIDENCE (needs live LLM calls against the tool — this is evaluation, not static analysis; flag as a deliberately different, much harder category if ever picked up).
</details>

<details>
<summary>smart-contract.md, mobile-app.md, design-system.md, embedded-firmware.md, data-pipeline-etl.md, browser-extension.md, emerging-archetypes.md</summary>

**smart-contract.md**: static vuln scanning (Slither), invariant fuzzing (Echidna), gas-cost regression (`forge snapshot`), proxy storage-layout validation (OpenZeppelin Upgrades) → NEW, real keyless tools, but a genuinely different tech stack (Solidity/Foundry) this portfolio may never contain — low priority unless a target repo actually matches `repo_type.py`'s smart_contract signal. Formal verification → OUT_OF_SCOPE(keyed, Certora).

**mobile-app.md**: permission-vs-disclosure parity, plaintext-secret-in-bundle scanning, mobile SAST/DAST (MobSF covers several rows at once — one collector, not three), target-SDK-version currency → NEW, real tools, same "only relevant if repo_type.py flags mobile_app" caveat. Code-signing hygiene, phased-rollout release-health → OUT_OF_SCOPE(needs a keychain/live crash-reporting service).

**design-system.md**: per-component accessibility scoring (axe-core against Storybook stories), design-tokens single-source-of-truth presence (Style Dictionary config) → NEW, concrete. Visual regression, design-to-code drift, cross-app change-impact → OUT_OF_SCOPE(Chromatic/Percy/Figma API, all keyed services).

**embedded-firmware.md**: MISRA C/C++ compliance (Cppcheck), memory-safety static analysis (Clang Static Analyzer) → NEW, real, keyless. WCET/deadline analysis, firmware security testing, hardware-in-the-loop CI, secure-boot/OTA verification → OUT_OF_SCOPE(all need target hardware or emulation this tool has no access to).

**data-pipeline-etl.md**: dbt/Airflow-specific presence checks (data-quality-test config, DAG idempotency patterns, lineage config, freshness/SLA config, schema-contract definitions) → NEW, all presence/config-parsing against a specific framework's own files — legitimate if narrow. Warehouse query-cost regression → OUT_OF_SCOPE(needs a paid/live warehouse connection).

**browser-extension.md**: manifest/permission linting (web-ext), MV3 remote-code/CSP compliance grep, bundled-secret scanning (overlaps security.py — extend, don't duplicate), update-channel-integrity check → NEW/EXTEND, concrete and cheap (manifest.json is small, well-specified). Privacy-disclosure parity → OUT_OF_SCOPE(store-side, manual).

**emerging-archetypes.md**: agent-to-agent handoff governance (LangGraph/CrewAI control-flow contract presence) → NEW, narrow. Frame-budget/asset-budget validation (game engines), cross-agent trace/replay → OUT_OF_SCOPE(needs a live game-engine runtime or a keyed tracing service like LangSmith/Langfuse).
</details>

## Checklist gap-analysis backlog (2026-09-06)

Full criteria-by-criteria classification (COVERED/PARTIAL/GAP) against dev-branch-today across all
24 checklist files, ~508 criteria: 22 COVERED, ~44 PARTIAL, ~442 GAP. Six collectors already in
flight in separate worktrees (`tooling_drift`, `agent_skill_quality`, `microservices_topology`,
`meta_repo_health`, `pr_review`, `notebook_quality`) are excluded from GAP counts above — see the
"New collectors" list earlier in this doc, don't duplicate. Prioritized backlog below is
genuinely additive to that list; picked up in order roughly matching payoff-per-file-touched.

- **`license_compliance.py`** — built (`pip-licenses`/`license-checker`/`cargo-license`/
  `go-licenses`, dispatched by detected language same as `lint_quality.py`), **not yet merged**:
  independent verification found the SPDX BSD-3-Clause detector's exact-substring match breaks on
  real line-wrapped LICENSE text; fix in progress on `worktree-agent-a67506e510d5a7ffc`.
- **`flag_debt.py`** — built (feature-flag SDK presence + stale/orphaned flag detection, answering
  polyrepo.md's and microservices.md's feature-flag-SDK-presence rows above), **not yet merged**:
  verification found an oversized test file and a stale base; split + rebase in progress on
  `worktree-agent-a435f394ecf0e53f2`.
- **`api_surface_diff.py`** — medium-large, needs the target repo's toolchain to actually build
  (heavier precondition than most collectors here). Covers backward-compat/semver discipline across
  4 checklist files — highest cross-file payoff on this list, but **new external tool deps**
  (`api-extractor`/`apidiff`/`cargo-semver-checks`/`griffe`) — flagged for human sign-off per
  AGENTS.md §2.2, not dispatched until that happens.
- **`slither_scan.py`** — smallest item here, smaller than `meta_repo_health.py`. Covers
  smart-contract.md's static-vuln-scanning (the flagship criterion for an otherwise fully-GAP
  archetype `repo_type.py` already detects). Shell out to `slither .`, parse its JSON output.
- **`docs_knowledge_hygiene.py`** — medium, multi-signal shape like `microservices_topology.py`.
  Covers docs-repo.md + ai-knowledge-base.md content-freshness/broken-links/readability/frontmatter-
  schema/token-budget (7 criteria, one shared file-tree walk). `lychee` (links), `textstat`
  (Flesch-Kincaid), `tiktoken` (token counts), plain frontmatter-YAML + JSON-Schema check,
  git-log-staleness-vs-frontmatter-date diff (same shape as `escape.py`'s SZZ window logic).
- **`pipeline_contract_presence.py`** — small-medium, "presence + CI-wiring" template like
  `e2e_quality.py`/`performance.py`. Covers data-pipeline-etl.md's data-quality-test/freshness/
  schema-contract config presence (3 criteria). Parse `dbt_project.yml` + `schema.yml`/`sources.yml`
  for `tests:`/`freshness:`/`contract:` keys — config-presence only, no live warehouse execution.
- **`lifecycle_script_risk.py`** — small-medium. Covers library-package.md's install-time
  lifecycle-script risk + CI-hardening (2 criteria). Grep `package.json` pre/postinstall +
  `setup.py` sdist-build equivalent; shell out to `zizmor`/`actionlint` against `.github/workflows/`.
- **Extend `inventory.py`/`effort.py`** — onboarding time-to-first-commit + doc/changelog hygiene
  (3 criteria), pure git-log arithmetic, not worth a standalone package.
- **Extend `ci_gates.py`** — gate-vs-advisory, pre-commit presence, OS-matrix, lockfile discipline,
  fuzz-test presence (5 criteria) + developer-tools.md cross-platform (1) — same `TEST_RE`-style
  workflow-step regex matching the file already does.
- **Extend `supply_chain.py`** — IaC module-pinning + state-file hygiene (2 criteria) — same IaC
  tree it already walks for Trivy config-mode.
- **`hardcoded_endpoint_check`** — tiny, fold into `security.py`'s semgrep custom rules rather than
  a new file (one Semgrep rule for literal IPs/hostnames bypassing service discovery).
- **Portfolio-wide contribution-inequality** — tiny, `synthesize.py` tweak reusing `inventory.py`'s
  Gini math regrouped by author across the whole portfolio (distinct from bus-factor's per-repo
  framing per the checklist's own text).

**Explicitly not recommended**: rag-vector-store.md (12 criteria, needs a live vector DB or
LLM-judge eval, almost nothing git-clone-analyzable); "practice-maturity benchmarking" criteria
recurring across 3 files (a written comparison doc, not a measurable data point — a report-template
prompt, not a collector); monorepo.md's build-system-health section (9 criteria, needs
vendor-specific build-tool telemetry disproportionate to likely portfolio composition).

**Unresolved from this pass** (flag before trusting the classification): does `depgraph.py` surface
cycle-detection/fan-in-fan-out as findings or only build graph edge data; does `supply_chain.py`'s
Trivy mode cover Dockerfile-hardening or only Terraform/k8s; does `e2e_quality.py` read deep enough
for cross-browser-coverage vs. presence-only. `tooling_drift`/`notebook_quality` classifications
above are name-inference only (zero source read this pass) — low confidence.

## Verify repo-analyser's own process health (memory, CPU, threads)

Not yet done: repo-analyser runs many external subprocesses across a portfolio (one lizard/jscpd/
semgrep/gitleaks/osv-scanner/mutmut/Stryker invocation per repo, sometimes dozens of repos per
run), and nothing currently confirms its own Python process doesn't accumulate memory across that
— open file handles, temp directories, subprocess objects, growing in-memory lists — over a long
portfolio run. Given this session's own crash history (`docs/METHODOLOGY.md` #23), resource
behavior here isn't a hypothetical concern.

Concrete, real tools to add for this, not a generic "add profiling" placeholder:

- **Memory-leak detection**: `tracemalloc` (stdlib, zero new dependency — snapshot allocations
  before and after a full portfolio run, diff the top allocators) as the first, cheapest check.
  `memray` (Bloomberg, MIT) if a deeper look is needed — can wrap a full CLI invocation
  (`memray run -- python3 -m repo_analyser analyze ...`) and produce a flamegraph without any code
  changes to this tool.
- **CPU profiling**: `py-spy` — a sampling profiler that attaches to a running process by PID with
  no code changes, well suited to a tool that spends most of its wall-clock time waiting on
  subprocesses rather than doing its own computation (it will show that split clearly: time in
  this tool's own Python vs. time inside `lizard`/`jscpd`/etc.). `scalene` as an alternative with
  built-in memory+CPU line-level attribution in one run.
- **Thread optimization checks**: verified via `grep` (2026-09-05) that `src/repo_analyser/`
  currently has zero `threading`/`multiprocessing`/`ThreadPoolExecutor` usage of its own — every
  collector runs its subprocess calls sequentially. There is nothing to check here yet. Revisit
  only if/when this codebase actually introduces concurrency of its own (e.g., running multiple
  repos' collectors in parallel) — adding a thread-safety checker ahead of having any threads would
  be checking nothing.

Acceptance bar for this item, once picked up: run one of the above against a real, multi-repo
portfolio-scale invocation (not a synthetic fixture) and report real numbers — a passing check on
a toy input would be the same "denominator dishonesty" this repo's own methodology explicitly
argues against.

## Runtime performance / latency budget collector (`performance.py`)

**Detection built** (ADR-0003 slice): `performance.py` detects a declared budget (Lighthouse CI /
bundlesize / size-limit / artillery config or dependency) and whether it's wired into CI, mirroring
`e2e_quality.py`'s presence-only shape (`docs/ARCHITECTURE.md`'s "one collector = one external tool"
rule, ADR-0002) — writes `performance.csv`/`performance_summary.json`, read by
`per_repo_digest.py`'s `_AllData.performance`. Before this, confirmed absent via full-codebase grep
(2026-09-05): the only near-miss hits were `ontology.py`'s commit-message classifier (labels a
commit "perf" if its message mentions performance/latency — never measures anything) and
`escape.py`'s "fix latency" (calendar days a bug lived before a fix — a defect-lifecycle metric, not
application runtime latency).

**Still open: real benchmark execution.** `performance.py` only answers "is a budget declared and
enforced in CI" — it never runs one. Matching `testquality.py`'s "actually run it" philosophy (same
timeout discipline via `core.util.run()`): Go's `go test -bench=. -benchmem`, Python's
`pytest-benchmark` (only if the target already depends on it — never installed by this tool into a
target repo), JS/TS benchmark frameworks (`vitest bench`, `tinybench`). Report real numbers (ns/op,
allocations) as new columns on the same `performance.csv`, keeping the `repo` column every other
collector's CSV already has.

Acceptance bar for the execution half: run against a real target that has an actual benchmark suite
(not a fixture) and show the real numbers landing in `performance.csv`, then confirm
`per_repo_digest.py`'s performance section picks them up with only an additive change to
`_section_performance` (the budget-detection half of that section is already live and shouldn't
need to change).

## Recurring / CI-integrated runs

**Built**: `.github/workflows/analyze-reusable.yml`, a `workflow_call` reusable workflow a target
repo (or portfolio-meta-repo) invokes on a `schedule:` cron and/or via `workflow_run` after its own
E2E workflow completes — see README's "Recurring analysis" section for the exact caller snippets.
Caches `analyses/` between runs (`actions/cache`, private to the calling repo — never a public
artifact or a commit, since that output carries real secret-scan/CVE data) so `trends.py` has a
prior baseline from the second run onward.

**Verified**: YAML validity, correct `workflow_call` input/output structure, and the embedded shell
is `shellcheck`-clean (including a fix for interpolating `${{ inputs.* }}` directly into `run:`
script text — GitHub's own documented script-injection anti-pattern, caught by rerunning shellcheck
after writing it; now passed via `env:` instead, matching this codebase's existing "no unsanitized
input into a shell string" rule).

**Not verified, stated plainly**: never executed on a live GitHub Actions runner from this
environment (no sandboxed runner available here) — untested against a real caller workflow. Do
that before relying on it in production.

**Still open**: `trends.py` today diffs portfolio-wide numbers only. Whether it also needs a
per-repo-digest-aware diff (this specific repo's mutation score dropped, not just the portfolio
mean) is a real open question for whoever picks this up next, not assumed solved by this workflow
existing.
