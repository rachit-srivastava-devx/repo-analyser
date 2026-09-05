# Per-Pull-Request Review

The same repo can pass every check above and still take a bad change. These run at review time, scoped to just the diff — quality, security, and performance on the change itself, then how far its blast radius reaches.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **A diff is attached to an open pull/merge request** | `CI event check (e.g. github.event_name == 'pull_request')` — always an overlay, never exclusive |

## Audit Checklist

### Code Quality (Diff-Level)

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **New-code quality gate** | scores complexity, duplication, and coverage on just the lines this PR changed, so legacy debt can't hide a regression. | `SonarQube Community Edition (self-hosted)`, `diff-cover` |
| **PR size vs. reviewability** | labels or warns once additions+deletions cross a reviewable threshold; oversized diffs correlate with rubber-stamp approval. | `Danger.js`, `size-label-action` |
| **Diff-scoped lint annotations** | posts inline comments only on lines this PR touches, ignoring pre-existing violations elsewhere in the file. | `reviewdog -filter-mode=added` |
| **Review-rigor gate** | blocks merge until a CODEOWNERS-matched approver reviewed the changed paths, not just any teammate. | `GitHub required reviewers + CODEOWNERS`, `GitLab approval rules` |

### Security (Diff-Level)

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Diff-aware SAST** | scans only code changed since a baseline commit, reporting solely findings this PR introduces. | `Semgrep --baseline-commit`, `CodeQL PR code scanning` *(keyed)* |
| **New-dependency CVE/license gate** | diffs the manifest between base and head and fails on a newly introduced vulnerable or disallowed-license package. | `actions/dependency-review-action`, `OSV-Scanner (lockfile diff)` |
| **Diff-scoped secrets scan** | checks only the commits being pushed, not full history, so a leaked key blocks this PR specifically. | `Gitleaks protect --staged`, `GitHub push protection` |
| **Authz-sensitive path escalation** | changes under auth/permissions/IAM paths auto-require a security-team reviewer instead of standard review. | `CODEOWNERS on sensitive paths`, `branch protection rules` |

### Performance (Diff-Level)

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Benchmark regression gate** | runs the suite on this branch, compares against the base branch's stored results, and comments or fails past a threshold. | `github-action-benchmark`, `Bencher (self-hosted)` |
| **Bundle-size delta comment** | posts gzip/brotli size change per entry point directly on the PR. | `Compressed-Size-Action`, `size-limit` |
| **Web perf budget check** | runs against the PR's preview deploy and fails if Core Web Vitals regress past budget. | `Lighthouse CI (self-hosted server)` |
| **Query/latency benchmark delta** | compares p95 latency or per-request query count on affected endpoints, base vs. PR branch. | `k6 baseline-diff script`, `Prisma query logging (JS/TS)`, `pgx tracelog (Go)`, `sqlx log_slow_statements (Rust)`, `django-silk (Python)` |

### Blast Radius — Connected Repos & Internal Consumers

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Affected-project computation** | resolves exactly which internal packages/apps depend on the changed files so only real consumers rebuild/retest. | `nx affected`, `turbo --filter`, `bazel query rdeps` |
| **Consumer-driven contract gate** | blocks deploy unless every registered consumer has verified its contract still holds against this change. | `Pact Broker (self-hosted) can-i-deploy` |
| **Reverse-dependency lookup across a polyrepo** | finds every other repo importing the changed package/API when there's no shared build graph. | `Hound (self-hosted)`, `gh search code`, `Sourcegraph` *(keyed)* |
| **Auto-posted consumer list** | a bot comments the affected downstream services/teams on the PR so reviewers see blast radius without asking around. | `Backstage catalog relations (self-hosted)`, `custom gh pr comment bot` |

### Blast Radius — External Consumers & Public API

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Public API surface diff** | compares exported types/signatures against the last published version and flags accidental breaks. | `api-extractor (JS/TS)`, `apidiff (Go)`, `cargo-semver-checks (Rust)`, `griffe check (Python)` |
| **OpenAPI/GraphQL breaking-change check** | diffs the schema and fails when a change is breaking but not declared as one. | `oasdiff`, `graphql-inspector`, `buf breaking` |
| **Missing-changeset gate** | comments or fails when a PR touches a published package without a changeset declaring its semver bump. | `Changesets + changesets/action` |
| **Downstream-consumer breakage estimate** | surfaces who actually imports the changed public package before the release ships. | `deps.dev dependents`, `npm/pnpm why`, `Socket.dev dependents view` *(keyed)* |

### Dependency Impact

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **License allowlist check on new deps** | fails only on a newly introduced package whose license isn't pre-approved, ignoring the existing tree. | `actions/dependency-review-action`, `OSS Review Toolkit` |
| **CVE check scoped to the diff** | flags a known vulnerability only in the package version this PR adds or bumps to. | `actions/dependency-review-action`, `OSV-Scanner (diff-scoped)` |
| **Supply-chain health score for the new package** | maintenance activity, install scripts, and typosquat similarity scored before the dependency is allowed in. | `OpenSSF Scorecard`, `deps.dev`, `Socket.dev` *(keyed)* |
| **Lockfile-diff vulnerability scan** | scans exactly the packages that changed between old and new lockfile, not the whole tree. | `OSV-Scanner --lockfile diff` |

### Staleness & Future-Proofing

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **PR-age staleness gate** | auto-labels, pings, or closes a PR once it's sat open past a threshold with no activity. | `actions/stale` |
| **Stale-base / conflict-risk gate** | blocks merge until rebased onto current main; separately flags PRs many commits behind as high-risk before review. | `GitHub required-up-to-date branches`, `Kodiak (self-hosted)` |
| **Flexibility-reduction check** | fails CI when a diff hardcodes a previously configurable value or violates an architectural rule protecting a pluggable extension point. | `ArchUnit fitness functions`, `Deptrac` |
| **Reversibility gate** | a risky change must ship behind a flag rather than a bare deploy, so it can be turned off without a revert. | `Unleash (self-hosted)`, `OpenFeature`, `LaunchDarkly` *(keyed)* |
