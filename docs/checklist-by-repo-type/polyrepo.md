# Polyrepo

Many repos, one per service/team. The mirror image of monorepo's problems: instead of internal-boundary hygiene, the risk is drift between repos that no longer share a build, a lint config, or a review.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **catalog-info.yaml (Backstage), or a Cortex/OpsLevel/Port config referencing sibling repos** | `file presence check` |

## Audit Checklist

### Cross-Repo Code Duplication

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Clone detection across the fleet** | scan all repos for copy-pasted blocks that should have been a shared package. | `jscpd`, `PMD CPD` |
| **Shared-library adoption rate** | % of repos importing the sanctioned internal package vs. carrying an inlined copy. | `Sourcegraph (self-hosted)`, `ripgrep fleet-clone scan` |
| **Near-duplicate / semantic duplication search** | structurally similar functions with renamed variables that exact-clone detectors miss. | `Semgrep`, `PMD CPD --ignore-identifiers`, `NiCad` |
| **Duplication trend vs. repo count** | is duplicated logic growing faster than the fleet itself, signaling repo-splitting is outpacing shared-platform investment. | `jscpd (JSON export trended in CI)`, `Prometheus + Grafana` |

### Interdependency & Version-Skew Management

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Cross-repo dependency graph** | map of which repos consume which internal packages/services, used to estimate blast radius before a breaking change. | `Backstage (self-hosted)`, `Sourcegraph (self-hosted)`, `Neo4j Community Edition` |
| **Semver compliance auditing** | catches a breaking change shipped as a minor/patch bump by diffing the real API surface against the declared bump. | `oasdiff`, `buf breaking`, `api-extractor (TS)`, `apidiff (Go)`, `cargo-semver-checks (Rust)`, `griffe check (Python)` |
| **Dependency update lag** | how many versions behind each consumer is from the latest producer release, fleet-wide. | `Renovate (self-hosted)`, `Dependabot` |
| **Lockstep release coordination cost** | count and pain of releases requiring two-plus repos to deploy in a coordinated window. | `Argo CD sync waves`, `Backstage TechDocs runbook audit` |
| **Version compatibility matrix maintenance** | a maintained, tested record of which producer version works with which consumer version, or tribal knowledge. | `CI matrix jobs`, `Backstage TechDocs` |
| **Transitive fan-out depth** | how many repos a change ripples through once transitive (not just direct) consumers are counted. | `npm ls (JS/TS)`, `pipdeptree (Python)`, `go mod graph (Go)`, `cargo tree (Rust)`, `Backstage catalog graph traversal` |
| **Static-vs-runtime dependency reconciliation** | cross-check the inferred dependency graph against observed production wiring (live env-var/service exports), catching drift static analysis alone misses. | `kubectl config/secret export scripts`, `custom diffing script` |

### API & Contract Compatibility

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Consumer-driven contract testing coverage** | % of producer-consumer integration points backed by an executable contract instead of hope-and-E2E. | `Pact`, `Pact Broker (self-hosted)` |
| **"Can-I-deploy" gate usage** | deploy pipelines query contract-verification status before releasing a producer. | `Pact Broker can-i-deploy CLI` |
| **Schema/breaking-change detection** | automated API-surface diff on every PR, per protocol. | `oasdiff`, `graphql-inspector`, `buf breaking` |
| **Deprecation/sunset policy adherence** | deprecated endpoints tracked with a sunset date and consumer migration nudges instead of living forever. | `custom Sunset-header audit script`, `Kong Gateway Community` |
| **Contract-break incident count** | production incidents actually traced to an undetected cross-repo contract break. | `GitHub/GitLab Issues (root-cause label)`, `Grafana OnCall` |

### CI/CD Gate Consistency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Golden-path CI template adoption** | % of repos using the org's centrally maintained pipeline vs. a bespoke one that silently drifts. | `GitHub Actions reusable workflows`, `GitLab CI includes` |
| **Required-check parity** | lint/test/security/coverage checks actually marked required in branch protection on every repo, not optional on some. | `GitHub/GitLab API scripted audit`, `org-wide repo rulesets` |
| **Lint/formatter config drift** | one canonical config vs. each repo forking and diverging. | `fleet-clone config-diff script`, `shared config package` |
| **Coverage gate threshold parity** | the enforced minimum coverage % is identical across repos of the same tier, not quietly lowered per-repo. | `lcov/coverage.xml threshold script`, `Prometheus Pushgateway` |
| **Gate enforcement vs. mere presence** | a security/quality scan actually blocks merge/deploy on failure, not just runs and reports into an ignored dashboard. | `GitHub/GitLab branch-protection API audit` |
| **Pipeline flakiness and duration fleet-wide** | aggregate flaky-job and pipeline-duration trends across all repos, invisible without a fleet rollup. | `ReportPortal (self-hosted)`, `GitHub/GitLab Actions API script` |

### Release Orchestration & Deployment Sequencing

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Dependency-aware deploy ordering** | a defined, ideally automated order for deploying interdependent services rather than tribal knowledge. | `Argo CD sync waves`, `Spinnaker` |
| **Cross-repo rollback coordination** | repo A can roll back without breaking repo B, which already adopted its new contract. | `Unleash (self-hosted)`, `Flagsmith (self-hosted)` |
| **Deployment blast-radius mapping** | the set of downstream repos/services a shared change affects is known before it ships. | `Istio + Kiali`, `Grafana Tempo service graph` |
| **Release cadence consistency** | fixed release trains vs. ad hoc per-repo releases; ad hoc raises coordination toil and the odds of an untested combination reaching prod. | `GitHub/GitLab Releases API script`, `Backstage catalog tracking` |
| **Environment promotion parity** | every repo follows the same dev→staging→prod gate sequence instead of some skipping staging under pressure. | `Argo CD`, `Flux + Flagger (self-hosted)` |
| **DORA metrics fleet-wide** | deployment frequency, change failure rate, MTTR rolled up across the whole fleet to surface systemically riskier repos. | `Four Keys (Google, OSS)`, `GitHub/GitLab API rollup script` |

### Discoverability & Documentation Fragmentation

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Central service catalog coverage** | % of repos actually registered in the org's catalog vs. "shadow" repos nobody indexed. | `Backstage (self-hosted)` |
| **README completeness/consistency** | every repo's README covers the same required sections (owner, how to run, how to deploy), checked mechanically. | `custom README linter script`, `markdownlint-cli` |
| **"Who owns this" time-to-answer** | how long it takes a random engineer to find the accountable team for an arbitrary repo. | `codeowners-validator`, `Backstage catalog ownership audit` |
| **API spec centralization** | OpenAPI/AsyncAPI/GraphQL schemas published to one discoverable portal instead of living only inside each repo. | `Backstage TechDocs`, `Redoc / Swagger UI` |
| **Cross-repo search capability** | one query searches "does this already exist" across the entire fleet instead of dozens of separate greps. | `Sourcegraph (self-hosted)`, `Hound` |
| **ADR discoverability** | architecture decisions captured and findable centrally instead of buried in Slack/PR comments. | `adr-tools / Log4brains`, `Backstage catalog ADR links` |

### Ownership Clarity & Repo Hygiene

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **CODEOWNERS presence and accuracy** | every repo maps to a real, currently staffed team, audited on a schedule rather than trusted at creation time. | `GitHub/GitLab API sweep`, `codeowners-validator` |
| **Bus-factor / knowledge concentration per repo** | the repo's history is dominated by one contributor who has since left or moved teams. | `code-maat`, `gitinspector` |
| **Staleness/abandonment detection** | last-commit age, open-PR age, unmerged automated-update backlog as neglect signals, aggregated fleet-wide. | `GitHub/GitLab API scripted dashboard`, `Backstage lifecycle annotation` |
| **Archival policy enforcement** | dead repos are actually archived/marked read-only on a defined trigger instead of left live to confuse newcomers. | `Backstage catalog lifecycle field`, `scripted archive-status sweep` |
| **Repo creation governance** | new repos scaffold from an approved template instead of reinventing CI/lint/structure each time. | `Backstage Software Templates`, `cookiecutter` |
| **Repo-to-team ratio / sprawl trend** | repo count growing faster than headcount, a leading indicator of future ownership gaps. | `GitHub/GitLab API pull`, `Grafana trend dashboard` |

### Security Posture Consistency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **SAST coverage parity** | static analysis actually enabled and enforced on every repo, not only the ones someone remembered. | `Semgrep`, `CodeQL CLI`, `GitHub/GitLab API workflow audit` |
| **SCA/dependency-vulnerability coverage parity** | every repo's dependency tree is actually scanned, org-wide. | `OSV-Scanner`, `Trivy`, `Dependabot alert audit` |
| **Secrets-scanning coverage** | push protection and historical secret sweeps enabled everywhere, not just where security remembered to configure it. | `Gitleaks`, `TruffleHog` |
| **Security debt aging/distribution** | mean time-to-remediate for criticals, bucketed per repo, to find where security debt is quietly concentrating. | `DefectDojo (self-hosted)`, `GitHub Security overview` |
| **License compliance scanning parity** | every repo checked for disallowed OSS licenses, not just the flagship ones. | `OSS Review Toolkit`, `ScanCode Toolkit` |
| **IaC/container scanning parity** | infra-as-code and container images scanned consistently across every repo that ships one. | `Trivy`, `Checkov` |
| **Named security contact per repo** | a real accountable owner for triage instead of an unwatched ticket queue. | `Backstage catalog security-contact annotation`, `SECURITY.md audit` |
| **Continuous CVE monitoring cadence parity** | every repo's CVE alerts feed the same on-call/triage flow on the same re-scan cadence, instead of some repos getting nightly scans and others only scanning on PR. | `Dependabot alerts org-wide enablement audit`, `centralized OSV-Scanner cron across the fleet` |

### Per-Repo Code Quality

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Cyclomatic complexity (CCN) per repo** | average/max CCN flagged against a threshold, tracked per repo and per language. | `lizard`, `radon`, `gocyclo` |
| **Duplication % per repo** | internal (not cross-repo) duplicated-lines density, since a single repo can rot on its own. | `jscpd`, `PMD CPD` |
| **Maintainability rating / code-smell count** | composite quality score per repo used to rank remediation priority. | `radon (MI)`, `SonarQube Community Edition` |
| **Static-analysis issue density** | linter warnings normalized per KLOC, comparable across differently sized repos. | `ESLint`, `Pylint`, `golangci-lint`, `Clippy` |
| **Hotspot analysis (complexity × churn)** | repos/files that are both complex and frequently changed, the highest-risk combination for bugs. | `code-maat`, `git-log churn script` |
| **Runtime/toolchain currency per repo** | is this repo still on an EOL language/framework version while the fleet standard has moved on. | `mise`, `asdf`, `Renovate` |

### Testing Depth (Unit, Mutation & Cross-Repo E2E)

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Unit coverage per repo, aggregated fleet-wide** | coverage per repo rolled into one org view so laggards are visible, not self-reported. | `native reporters (nyc, JaCoCo, coverage.py, go test -cover, cargo-tarpaulin)`, `custom rollup script` |
| **Mutation testing score per repo** | catches "coverage theater" (tests execute code but assert nothing) that line coverage can't see. | `Stryker`, `PIT`, `mutmut`, `go-mutesting`, `cargo-mutants` |
| **Cross-repo E2E/integration coverage** | flows spanning multiple services/repos have a real test exercising the actual boundary, not just each side's mocks. | `Playwright`, `Cypress`, `Testcontainers` |
| **Contract-test-as-integration-proxy coverage** | % of cross-repo integration points covered by a consumer-driven contract vs. relying entirely on brittle E2E. | `Pact + self-hosted Pact Broker` |
| **Fleet-wide flaky-test rate** | flaky tests compound badly once E2E suites cross repo boundaries; tracked centrally so no single repo's flakiness hides. | `scripted CI API rerun-history sweep`, `pytest-flakefinder` |
| **Cross-repo E2E suite ownership** | the suite spanning repos often has no natural owner; audited explicitly rather than assumed. | `CODEOWNERS`, `codeowners-validator` |
| **Test-environment topology parity** | the shared staging/E2E environment actually mirrors the real multi-repo prod topology instead of a stale subset giving false confidence. | `OpenTofu/Terraform plan diff`, `Atlantis` |

### Toil & Fleet-Wide Developer Efficiency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Shared-dependency bump toil** | PRs required and time-to-merge for rolling one version bump across N repos, the canonical polyrepo tax. | `Renovate (self-hosted)`, `Dependabot` |
| **Repos touched per "simple" change** | sampled or tracked count of repos a typical feature/bugfix must touch, a direct coupling proxy that should trend down. | `scripted API linked-PR sweep`, `manual sampling audit` |
| **Average PR lead time across the fleet** | DORA lead-time aggregated org-wide, since a few slow repos hide in a per-repo view. | `Apache DevLake (self-hosted)` |
| **Cross-team PR wait time** | time a PR sits waiting on sign-off from another team's repo before work can continue. | `Apache DevLake`, `scripted review-request timestamp diff` |
| **Changelog/release-note aggregation toil** | fleet-wide release-notes compilation automated and rolled up, or hand-copied from N repos every release. | `Changesets`, `release-please`, `git-cliff` |
| **Redundant CI spend** | identical boilerplate steps re-run cold in every repo's pipeline with no shared caching, inflating time and bill. | `GitHub Actions usage API`, `self-hosted runners` |
| **Local multi-repo bootstrap time** | time to get a feature spanning N repos running locally, often gated on docker-composing several services at once. | `timed bootstrap harness script` |
| **Cross-repo refactor cost** | cost of applying one mechanical change across every repo that needs it, absent monorepo-wide codemod tooling. | `ast-grep`, `Comby`, `jscodeshift/ts-morph` |

### Repo Sprawl & Fleet Governance

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Total repo count and growth rate** | raw sprawl signal tracked over time against team/org size. | `scripted GitHub/GitLab API sweep`, `Grafana` |
| **Golden-path template adoption** | % of existing repos actually scaffolded from (and kept in sync with) the approved template. | `Backstage Software Templates`, `scheduled drift-check script` |
| **Zombie/duplicate repo detection** | near-identical repos built by different teams solving the same problem because the first one wasn't discoverable. | `Hound (self-hosted)`, `jscpd fleet-wide` |
| **Naming-convention consistency** | repo names follow a predictable scheme so search and catalog tooling actually work. | `scripted API naming lint`, `Backstage catalog lint` |
| **Repo lifecycle labeling** | every repo tagged experimental/production/deprecated so audits and tooling treat them differently. | `Backstage catalog lifecycle field` |

### Build & Package Registry Consistency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Internal package registry hygiene** | shared libraries actually published and versioned through a registry instead of distributed via git submodules or copy-paste. | `Verdaccio (self-hosted)`, `Sonatype Nexus OSS` |
| **Lockfile enforcement per repo** | committed lockfiles that CI verifies are fresh, not silently regenerated, so builds are reproducible repo-to-repo. | `npm ci / pnpm --frozen-lockfile`, `go mod verify`, `poetry check --lock`, `cargo build --locked` |
| **Language/runtime version matrix across repos** | how many distinct Node/Python/Go/Java versions are live fleet-wide, and whether the spread is intentional or drift. | `asdf`, `mise` |
| **Build-tool config consistency** | Docker base images, Makefile/Taskfile targets follow one convention so any engineer can build any repo the same way. | `Hadolint`, `shared devcontainer.json templates` |

### Atomic Change Coordination Risk

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Cross-repo atomic-change frequency** | how often a single logical change requires coordinated, non-atomic commits across two-plus repos — the structural risk polyrepo carries that monorepo doesn't. | `scripted API cross-reference sweep` |
| **Expand-contract pattern adherence** | breaking changes roll out via backward-compatible expand → migrate consumers → contract phases instead of a single flag-day cutover. | `oasdiff`, `buf breaking` |
| **Inconsistency-window duration** | how long the fleet can run "half-migrated," some repos on the old contract and some on the new, before convergence. | `Argo CD deploy history`, `deploy-timestamp diff script` |
| **Feature-flag decoupling usage** | deploy is decoupled from release so a multi-repo rollout doesn't need to land atomically. | `Unleash (self-hosted)`, `Flagsmith (self-hosted)` |
| **Rollback blast radius** | if repo A rolls back, how many other repos' currently-deployed versions become incompatible as a result. | `Backstage catalog relations`, `version-matrix script` |

### Access Control & Policy-as-Code Consistency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Branch protection rule parity** | required reviewers, required checks, force-push restrictions consistent across repos of the same tier instead of ad hoc per repo. | `OpenTofu/Terraform GitHub provider`, `native org-wide rulesets` |
| **Admin/permission sprawl** | how many repos each person has admin on, and whether that matches actual ownership. | `scripted API permissions sweep`, `CODEOWNERS cross-reference` |
| **Policy-as-code enforcement** | org-wide standards enforced programmatically rather than by convention or wiki page. | `Open Policy Agent (OPA)`, `Conftest` |
