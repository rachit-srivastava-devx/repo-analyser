# Single Repo

One repo, one codebase — no network boundary between parts, so discipline has to be self-imposed. Design docs through team process, all in one place.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **No workspace file; one manifest at root** (package.json, pyproject.toml, go.mod, Cargo.toml) | `default assumption when nothing below matches` |

## Audit Checklist

### Architecture & Design Documentation

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **HLD freshness** | one current doc covering components, data/control flow, external dependencies, deployment topology; re-validated every release. | `Structurizr Lite`, `C4-PlantUML`, `arc42 template` |
| **LLD completeness** | per-module design covering algorithms, data structures, state machines, edge cases, written before or alongside implementation. | `PlantUML`, `Mermaid CLI` |
| **ADR coverage & discipline** | every non-trivial architectural decision recorded with context and consequences, immutable once accepted. | `adr-tools`, `Log4brains`, `MADR template` |
| **Design-vs-implementation drift** | periodic check that diagrams still match real module boundaries and the dependency graph. | `dependency-cruiser (JS/TS)`, `go-arch-lint (Go)`, `cargo-modules (Rust)`, `import-linter (Python)` |
| **Public interface documentation** | REST/GraphQL/RPC surface specified in one versioned source of truth, not reverse-engineered from code. | `Spectral`, `graphql-schema-linter`, `Buf lint` |
| **Runbook & operational-doc coverage** | deploy, rollback, on-call, and known-failure-mode procedures documented and periodically dry-run. | `Backstage TechDocs`, `Grafana OnCall`, `Rundeck` |
| **Decision reversibility tagging** | one-way-door vs. two-way-door decisions flagged so review effort concentrates on irreversible ones. | `MADR template (custom tag)`, `adr-tools` |

### Codebase Structure & Internal Modularity

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Circular dependency detection** | import cycles between internal modules hide coupling and block future extraction. | `madge (JS/TS)`, `godepgraph (Go)`, `cargo-modules --acyclic (Rust)`, `pydeps (Python)` |
| **Layering/boundary enforcement** | architectural rules (e.g. domain must not import infra) enforced at build time, not by review memory. | `dependency-cruiser (JS/TS)`, `go-arch-lint (Go)`, `cargo-modules (Rust)`, `import-linter (Python)` |
| **God class/module detection** | oversized modules accumulating unrelated responsibilities become change bottlenecks and merge-conflict magnets. | `PMD (GodClass rule)`, `SonarQube Community Edition`, `Lizard` |
| **Fan-in/fan-out hotspots** | modules with abnormally high dependents or dependencies mark refactor/extraction candidates. | `dependency-cruiser (JS/TS)`, `gometric (Go)`, `cargo-modules (Rust)`, `pydeps (Python)` |
| **Module/package size budget** | caps on files-per-package and LOC-per-module keep bounded contexts navigable as the repo grows. | `cloc`, `SonarQube Community Edition` |
| **Configuration & feature-flag debt** | stale or orphaned flags and unused config keys left after rollout accumulate invisible branching complexity. | `Unleash (self-hosted)`, `Flagsmith (self-hosted)`, `Knip` |

### Interface & API Contract Stability

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Backward-compatibility discipline** | breaking changes to the public surface gated behind a semver-major bump and a deprecation window. | `graphql-inspector`, `oasdiff`, `buf breaking` |
| **Spec-to-implementation conformance** | published schema kept in lockstep with actual handler behavior via automated contract tests, not manual review. | `Dredd`, `Prism`, `Schemathesis` |
| **Deprecation policy enforcement** | deprecated endpoints/fields carry sunset dates and usage telemetry before removal. | `RFC 8594 Sunset-header audit script`, `Kong Gateway (OSS)` |

### Code Quality Metrics

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Code duplication %** | near-identical blocks signal missed abstraction and multiply the cost of every bug fix. | `jscpd`, `PMD CPD`, `SonarQube Community Edition` |
| **Cyclomatic complexity (CCN)** | count of independent paths through a function; elevated values correlate with defect density and poor testability. | `Lizard`, `ESLint (complexity rule)` |
| **Cognitive complexity** | how hard code is for a human to follow (nesting, control-flow breaks), distinct from raw branch count. | `SonarQube Community Edition`, `eslint-plugin-sonarjs` |
| **Coupling & cohesion** | afferent/efferent coupling plus lack-of-cohesion (LCOM) flag brittle, poorly-bounded components. | `dependency-cruiser metrics (JS/TS)`, `gometric (Go)`, `cargo-coupling (Rust)`, `Radon (Python)` |
| **Dead code %** | unreachable functions, unused exports, unreachable branches inflate maintenance surface for zero value. | `Knip (JS/TS)`, `deadcode (Go)`, `rustc dead_code lint (Rust)`, `Vulture (Python)` |
| **Code smell density** | smells per KLOC (long parameter lists, feature envy, shotgun surgery) as a leading refactor-need indicator. | `SonarQube Community Edition`, `Code Climate CLI (OSS engine)`, `PMD` |
| **File/function size limits** | hard caps on LOC per file/function catch god-functions before they metastasize. | `ESLint max-lines (JS/TS)`, `golangci-lint funlen (Go)`, `Clippy too_many_lines (Rust)`, `Pylint too-many-lines (Python)` |
| **Type-safety coverage** | share of code under strict static typing vs. escape hatches (any, untyped defs). | `type-coverage (JS/TS)`, `golangci-lint forcetypeassert (Go)`, `cargo-geiger (Rust)`, `mypy --strict (Python)` |
| **Concurrency safety** | data races and unsynchronized shared-state access on multi-threaded paths. | `Go race detector`, `ThreadSanitizer` |
| **Lint suppression density** | inline lint-disable/noqa comments as a proxy for rules being silenced rather than fixed. | `ESLint --report-unused-disable-directives (JS/TS)`, `golangci-lint nolintlint (Go)`, `rustc #[expect] attribute (Rust)`, `Ruff RUF100 (Python)` |
| **Intent-vs-implementation divergence** | infer a function's intended behavior from its history and callers, then flag where the actual code silently diverges (error-swallowing, misleading names, dead parameters). | `Ollama (local LLM)`, `PyDriller`, `Semgrep (custom rules)` |

### Performance & Resource Efficiency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Latency budget/SLOs** | p50/p95/p99 targets per endpoint or critical path tracked against an error budget. | `k6`, `Prometheus`, `Grafana`, `Sloth` |
| **Memory leak detection** | growing heap/RSS under sustained load indicates un-released references or listeners. | `Chrome DevTools (JS/TS)`, `pprof heap profile (Go)`, `dhat-rs (Rust)`, `memray (Python)` |
| **CPU/resource profiling** | flame graphs identify hot functions and wasted allocation before reaching for more hardware. | `0x (JS/TS)`, `pprof (Go)`, `cargo-flamegraph (Rust)`, `py-spy (Python)` |
| **N+1 query detection** | per-request query count regressions from ORM lazy-loading. | `QueryGuard (JS/TS)`, `Unqueryvet (Go)`, `OpenTelemetry span-count audit (Rust)`, `django-silk (Python)` |
| **Algorithmic complexity hotspots** | Big-O blowups on hot paths, found by cross-referencing flame graphs with real input sizes. | `Scalene`, `FlameGraph`, `pprof/py-spy` |
| **Caching correctness** | cache-hit ratio, stale-read rate, invalidation-on-write correctness. | `Redis CLI (INFO stats)`, `redis_exporter`, `Grafana` |
| **Bundle/artifact size budget** | build-output size ceiling enforced in CI to prevent slow cold starts or page loads. | `webpack-bundle-analyzer`, `size-limit`, `bundlesize` |
| **Startup/cold-start time** | time from process launch to ready-to-serve; critical for autoscaling and serverless. | `hyperfine`, `custom CI timing harness` |
| **Load & soak testing** | sustained multi-hour load surfaces leaks and degradation short smoke tests miss. | `k6`, `Gatling`, `Locust` |
| **Slow-query monitoring** | production query latency tracked continuously against a threshold budget. | `pt-query-digest`, `pgBadger`, `SigNoz` |

### Data & Persistence Layer

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Migration reversibility** | every schema migration has a tested down-migration or a documented reason it's irreversible. | `Flyway Community`, `Liquibase Community`, `Django migrate --plan` |
| **Schema drift detection** | live DB schema diffed against migration history/ORM models to catch manual hotfixes. | `Atlas`, `pg-schema-diff`, `migra` |
| **Orphaned/redundant migrations** | dead or duplicate migration files accumulated over years of history. | `Prisma migrate status (JS/TS)`, `goose status (Go)`, `sqlx migrate info (Rust)`, `Django makemigrations --check (Python)` |
| **Index coverage vs. query patterns** | indexes matched to actual WHERE/JOIN predicates rather than guesswork. | `pg_stat_statements + EXPLAIN ANALYZE`, `PgHero`, `dexter` |
| **Boundary data validation** | constraints enforced at the DB layer, not solely in application code that can be bypassed. | `SchemaCrawler`, `custom constraint audit script` |
| **PII/sensitive-data column inventory** | data-classification tags so retention and access-control tooling has something to key off. | `piicatcher`, `Microsoft Presidio` |
| **Backup/restore drill verification** | restore-from-backup tested on a schedule, not just "backup job succeeded" logs. | `pgBackRest`, `WAL-G`, `restore-to-scratch drill script` |
| **Committed database file/dump hygiene** | a SQLite file, database dump, or seed-data fixture holding real (not synthetic) production data was never committed to the repo or its history — a distinct leak vector from credential-pattern secrets scanning, which a plain dump rarely trips. | `git-sizer`, `pre-commit-hooks (check-added-large-files)`, `Gitleaks (custom path rule)` |
| **Connection pool sizing & exhaustion testing** | pool size is set from measured concurrency rather than a copy-pasted default, and behavior under exhaustion — queueing vs. a hard failure — is verified under load rather than assumed. | `node-postgres pool stats (JS/TS)`, `pgxpool.Stat() (Go)`, `deadpool-postgres (Rust)`, `SQLAlchemy QueuePool events (Python)`, `PgBouncer (SHOW POOLS)` |
| **Query plan regression detection** | EXPLAIN ANALYZE output for hot queries is captured and diffed release-over-release, so a migration or ORM upgrade that silently drops an index — flipping a scan from index to sequential — is caught before it reaches production. | `pg_stat_plans`, `django-perf-rec (Python)`, `Prisma Optimize (JS/TS)` *(keyed)*, `pganalyze` *(keyed)* |
| **Row-level/column-level security policy correctness** | where the database itself enforces access control, RLS/CLS policies are exercised by actually connecting as the restricted role, not just reviewed by reading the policy definition. | `pgTAP`, `pg_prove`, `rlsautotest` |
| **Encryption at rest verification** | storage encryption is confirmed enabled against the live instance/volume configuration, not assumed because "the cloud provider handles it." | `Steampipe (aws_compliance mod)`, `Prowler`, `Scout Suite` |
| **Least-privilege database roles per service** | each service authenticates with a role scoped to only the tables and operations it needs, checked against actual GRANTs rather than every service sharing one superuser-equivalent connection string. | `pg_permissions`, `pgAudit` |
| **Read-replica lag monitoring** | replication lag is measured continuously and alerted on, since a stale-replica read is an easy-to-miss correctness bug in any read-scaled architecture. | `postgres_exporter (Prometheus)`, `PgHero`, `pt-heartbeat (Percona Toolkit)` |
| **SQL injection-specific testing** | beyond generic input-validation fuzzing, a named SQLi pass exists — a parameterization audit of query-construction call sites, or an actual payload-based injection test suite. | `sqlmap`, `njsscan (JS/TS)`, `gosec G201/G202 (Go)`, `sqlx query!/query_as! (Rust)`, `Bandit B608 (Python)` |
| **Table/index bloat & vacuum health monitoring** | table and index bloat plus dead-tuple counts are tracked over time so autovacuum tuning happens before bloat degrades query latency or forces an emergency REINDEX. | `pgstattuple`, `pg_repack`, `PgHero` |
| **Non-production data masking/anonymization** | a masked or synthetic copy — not a raw production snapshot — is what actually lands in staging/dev, closing the gap the PII inventory alone leaves between classifying sensitive columns and never exposing them outside production. | `postgresql_anonymizer`, `Tonic.ai` *(keyed)* |

### Security

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **SAST** | static scans catch injection and unsafe-deserialization patterns pre-merge. | `Semgrep`, `Bearer`, `SonarQube Community Edition` |
| **SCA / dependency vulnerability scanning** | third-party CVEs tracked against a live feed, blocking builds on critical severity. | `OSV-Scanner`, `Trivy`, `Grype` |
| **Secrets scanning** | committed credentials/API keys caught pre-commit and across full git history. | `TruffleHog`, `Gitleaks` |
| **AuthN/AuthZ correctness** | session handling, token expiry, permission checks tested against privilege-escalation and IDOR paths. | `OWASP ZAP (authenticated scan)`, `Autorize` |
| **OWASP Top 10 coverage** | each category mapped to a concrete test or scanner rule. | `OWASP ZAP baseline scan`, `OWASP ASVS checklist` |
| **Input validation & sanitization** | allowlist/boundary validation on every external input, enforced server-side. | `Semgrep (custom rules)`, `Jazzer.js (JS/TS)`, `go test -fuzz (Go)`, `cargo-fuzz (Rust)`, `Atheris (Python)` |
| **DAST** | black-box scan of the running app for exploitable endpoints. | `OWASP ZAP`, `Nuclei`, `Wapiti` |
| **SBOM & supply-chain provenance** | generated bill of materials plus build provenance to catch tampering or typosquatting. | `Syft`, `CycloneDX/SPDX tools`, `OpenSSF Scorecard` |
| **Container/image hardening** | base-image CVEs, non-root user, minimal layers for any repo shipping a container. | `Trivy image scan`, `Hadolint`, `Dockle` |
| **Security headers & transport config** | TLS config, CSP, HSTS, cookie flags checked against current baselines. | `Mozilla HTTP Observatory (self-hosted)`, `testssl.sh` |
| **Least-privilege review** | service accounts/API keys scoped to minimum needed permissions and rotated on schedule. | `Parliament`, `cloudsplaining`, `AWS IAM Access Analyzer` |
| **Rate limiting & abuse prevention** | throttling/quota enforcement on public endpoints prevents resource-exhaustion and brute-force abuse. | `k6 (abuse-traffic simulation)`, `Kong Gateway (OSS)` |
| **Continuous CVE monitoring (post-deploy)** | the deployed app's dependency tree is re-scanned on a schedule after release, not just once at build/PR time, so a CVE disclosed after ship still gets caught and paged. | `Dependabot security alerts`, `OSV-Scanner (scheduled cron)`, `Trivy (server mode)` |

### Testing & Verification

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Unit test coverage %** | line/branch coverage floor enforced in CI, read alongside coverage quality. | `Istanbul/nyc (JS/TS)`, `go test -cover (Go)`, `cargo-llvm-cov (Rust)`, `coverage.py (Python)` |
| **Mutation testing score** | injects small code mutations and measures what fraction of tests actually catch them, exposing assertion-free "coverage theater." | `Stryker (JS/TS)`, `gremlins (Go)`, `cargo-mutants (Rust)`, `mutmut (Python)` |
| **Integration test coverage** | cross-module and data-layer paths exercised against real(ish) dependencies instead of mocks. | `Testcontainers`, `Newman (Postman CLI)` |
| **Flaky test rate** | intermittently failing tests erode trust in CI and get silently skipped if untracked. | `jest.retryTimes (JS/TS)`, `go test -count (Go)`, `cargo-nextest --retries (Rust)`, `pytest-flakefinder (Python)` |
| **Test pyramid shape** | ratio of unit : integration : E2E tests; an inverted pyramid means a slow, brittle suite. | `Jest --listTests (JS/TS)`, `go test -list (Go)`, `cargo test -- --list (Rust)`, `pytest --collect-only (Python)` |
| **Test suite execution time** | full-suite runtime tracked as a first-class budget so the feedback loop doesn't silently degrade. | `jest-slow-test-reporter (JS/TS)`, `go test -json timing (Go)`, `cargo nextest (Rust)`, `pytest --durations (Python)` |
| **Snapshot test overuse** | frontend snapshot diffs that get rubber-stamped without review provide false confidence. | `Jest --ci`, `.snap churn-rate script` |
| **Contract/schema tests** | API responses validated against the published schema so consumers can't silently break. | `Pact + Pact Broker`, `schemathesis`, `Dredd` |
| **Property-based & fuzz testing** | generated/randomized inputs catch edge cases example-based tests miss. | `fast-check (JS/TS)`, `go test -fuzz (Go)`, `cargo-fuzz (Rust)`, `Hypothesis (Python)` |
| **Test data & fixture hygiene** | fixtures kept minimal, deterministic, and order-independent to avoid flaky ordering bugs. | `factory_boy`, `Faker`, `FactoryBot` |
| **Defect escape rate (introduction-dated)** | trace each bug back to the commit that introduced it, not just when it was fixed; track escape rate per cohort plus time-to-fix while live in production. | `PyDriller`, `SZZUnleashed` |

### End-to-End & Browser Testing

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **E2E suite health** | pass/fail trend of the E2E suite tracked as its own CI signal, kept separate from unit and integration health. | `Allure Report (JS/TS/Go/Rust/Python)` |
| **Visual regression testing** | screenshot diffing against a committed baseline catches unintended layout/style changes functional assertions don't see. | `Playwright toHaveScreenshot (JS/TS, Python)`, `chromedp/Rod + go-pixmatch (Go)`, `thirtyfour + image-compare (Rust)` |
| **Cross-browser/device coverage** | the E2E matrix actually executes against every rendering engine the product claims to support, not just Chromium. | `Playwright (Chromium/Firefox/WebKit) (JS/TS, Python)`, `playwright-community/playwright-go (Go)`, `thirtyfour via WebDriver (Rust)` |
| **E2E flake rate & quarantine** | E2E is typically the flakiest tier; failure/retry history is tracked and quarantined separately from unit-test flakiness. | `Playwright Test retries (JS/TS)`, `gotestsum --rerun-fails (Go)`, `cargo-nextest --retries (Rust)`, `pytest-rerunfailures (Python)` |
| **Trace/video/DOM-snapshot capture on failure** | a failed E2E run leaves a trace, video, and DOM snapshot behind so it can be debugged from the CI artifact alone. | `Playwright Trace Viewer (JS/TS, Python, Rust)`, `playwright-go tracing (Go)` |
| **Test parallelization/sharding** | the E2E suite is sharded across workers so it doesn't become the slowest stage of CI as it grows. | `Playwright --shard (JS/TS, Python)`, `gotesplit (Go)`, `cargo-nextest --partition (Rust)` |
| **Network mocking/interception fidelity** | intercepted/mocked network responses in E2E tests are contract-verified against the real API instead of silently drifting. | `Pact (pact-js/pact-go/pact_consumer/pact-python)` |
| **Accessibility checks within E2E** | automated a11y assertions run inline as part of the E2E pass itself, not only as a separate periodic audit. | `@axe-core/playwright (JS/TS)`, `axe-playwright-python (Python)`, `axe-core via script eval (Go/Rust)` |
| **Selector/locator resilience** | tests query elements the way a user would (role, label, test-id) rather than brittle CSS/XPath paths that break on refactors. | `getByRole/getByTestId (all Playwright bindings)` |
| **E2E execution time budget** | full-suite runtime tracked against an explicit budget, since E2E suites tend to grow unboundedly as flows are added. | `Playwright HTML/JSON reporter (JS/TS, Python)`, `go test -json timing (Go)`, `cargo nextest (Rust)` |

### Reliability & Observability

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Error handling consistency** | a uniform error/exception taxonomy instead of ad hoc try/catch-and-swallow blocks. | `SonarQube Community Edition`, `Error Prone`, `golangci-lint (errcheck)` |
| **Structured logging coverage** | logs emitted as structured events with correlation IDs, not raw string concatenation. | `OpenTelemetry`, `Grafana Loki`, `OpenSearch` |
| **Metrics & alerting coverage** | golden-signal metrics exported and alerted on with sane, non-flappy thresholds. | `Prometheus`, `Alertmanager`, `Grafana` |
| **Internal tracing/span coverage** | even a single service benefits from tracing internal spans (DB calls, external calls) for latency attribution. | `OpenTelemetry`, `Jaeger`, `Grafana Tempo` |
| **Incident & postmortem process** | blameless postmortems with tracked action items and recurrence checks. | `Netflix Dispatch`, `in-repo postmortem template` |
| **Health/readiness probe correctness** | liveness/readiness endpoints reflect real dependency health, not just "process is up." | `k8s probe-config review`, `Blackbox Exporter`, `Uptime Kuma` |
| **Graceful degradation & fault injection** | behavior under dependency failure/latency injection verified, not assumed. | `Chaos Mesh`, `LitmusChaos`, `chaos-monkey-spring-boot` |
| **Error-budget burn-rate tracking** | SLO-breach velocity tracked so teams know when to freeze features for reliability work. | `Sloth`, `Prometheus burn-rate rules` |
| **Alert signal-to-noise ratio** | ratio of actionable to non-actionable pages, tracked to prevent on-call desensitization. | `Grafana OnCall`, `Karma` |
| **Idempotency of mutating operations** | retried requests don't double-charge or double-create. | `idempotency-key design review`, `Toxiproxy`, `Testcontainers` |

### Maintainability & Technical Debt

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Documentation freshness** | docs linked to a code version and flagged stale when referenced code changes without a doc update. | `Vale`, `markdown-link-check` |
| **Onboarding time-to-first-commit** | days from repo access to first merged PR, a direct proxy for setup friction and doc quality. | `git-log first-commit script` |
| **Tech debt backlog size & age** | count and average age of tracked debt tickets, watched for silent growth. | `SonarQube Community Edition`, `ripgrep TODO/FIXME audit` |
| **Dependency staleness** | how far behind latest major/minor each dependency sits, and time-to-upgrade after release. | `Renovate (self-hosted)`, `Dependabot` |
| **License compliance** | every dependency's license checked against an allowlist to avoid copyleft contamination. | `OSS Review Toolkit`, `ScanCode Toolkit`, `pip-licenses` |
| **Code churn / hotspot risk** | files with high change-frequency × high complexity flagged as the riskiest refactor/test-investment targets. | `code-maat`, `git-quick-stats`, `Lizard` |
| **Doc-comment coverage** | public functions/modules carry accurate doc-comments consumable by IDEs and doc generators. | `eslint-plugin-jsdoc (JS/TS)`, `revive exported rule (Go)`, `rustdoc missing_docs lint (Rust)`, `interrogate (Python)` |
| **Changelog & release note discipline** | every release has a human-readable changelog generated or curated, not a raw commit dump. | `semantic-release`, `git-cliff` |

### Build, CI/CD & Developer Tooling

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Build time** | wall-clock CI build time tracked as a budget so regressions get caught before they become the norm. | `Bazel --profile`, `Gradle --profile` |
| **Build reproducibility** | the same commit produces a bit-identical or behavior-identical artifact regardless of machine or time. | `Bazel/Nix hermetic builds`, `diffoscope` |
| **Lint/format gate enforcement** | style and lint checks block merge rather than sitting advisory-only. | `ESLint/Prettier (JS/TS)`, `golangci-lint (Go)`, `rustfmt/Clippy (Rust)`, `Ruff (Python)` |
| **Pre-commit hook coverage** | fast local checks (format, lint, secret scan) catch issues before they ever reach CI. | `pre-commit framework`, `Husky + lint-staged` |
| **Static analysis quality gate** | merges blocked when new code drops below a complexity/duplication/coverage threshold. | `SonarQube Community Edition`, `jscpd + Lizard (custom gate)` |
| **CI flake/failure rate** | pipeline-level failure rate tracked separately from actual code defects. | `GitHub Actions Insights`, `Prometheus + Grafana` |
| **Lockfile & dependency-install discipline** | reproducible installs enforced via committed lockfiles and CI verification. | `npm ci (JS/TS)`, `go mod verify (Go)`, `cargo build --locked (Rust)`, `poetry check (Python)` |
| **Environment parity** | dev/CI/prod config differences tracked explicitly to avoid "works on my machine." | `dotenv-linter`, `Docker Compose parity checks` |

### Team Process & Collaboration

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Code review turnaround time** | median time from PR-open to first review and to merge, a leading indicator of delivery drag. | `Apache DevLake`, `GitHub/GitLab API script` |
| **Bus factor / knowledge concentration** | how many people can safely change each module without a departure creating an orphaned area. | `code-maat`, `git-fame`, `git-quick-stats` |
| **PR size distribution** | share of PRs above a reviewable LOC threshold; oversized PRs correlate with shallow, rubber-stamp review. | `Apache DevLake`, `gh pr list (custom script)` |
| **Review depth/rigor** | comments-per-PR and post-merge revert/hotfix rate as a proxy for genuine vs. rubber-stamp review. | `Apache DevLake`, `git-log revert/hotfix grep script` |
| **DORA metrics** | deployment frequency, lead time, change-fail rate, MTTR as the standard delivery-performance baseline. | `Four Keys`, `Apache DevLake` |
| **On-call load balance** | pages-per-person and off-hours interruption rate tracked to prevent burnout concentrating on a few people. | `Grafana OnCall`, `Karma` |

### Compliance, Privacy & Accessibility

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **GDPR/CCPA data-subject rights support** | verified, working deletion/export-on-request flows against the classified data inventory. | `custom DSAR integration-test suite`, `GitLab Issues (audit trail)`, `OneTrust` *(keyed)* |
| **Accessibility (a11y) conformance** | WCAG 2.1 AA checks automated and spot-checked with assistive tech for any repo shipping a UI. | `axe-core`, `Lighthouse CI`, `Pa11y` |
| **Audit logging completeness** | security-relevant actions logged immutably as compliance evidence. | `Wazuh`, `auditd` |
| **Data retention & deletion enforcement** | automated purge jobs verified to actually delete data per policy, not just assumed to run. | `Kubernetes CronJob + Testcontainers verification`, `pg_cron` |
