# Monorepo

Many packages/services, one shared history. Assumes the single-repo basics above already apply per-package — these are the concerns unique to scale: the build graph, cross-package boundaries, and CI cost.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **nx.json, turbo.json, pnpm-workspace.yaml, lerna.json, or rush.json at root** | `marker-file check script` |
| **WORKSPACE, WORKSPACE.bazel, MODULE.bazel, BUCK, or pants.toml at root** | `marker-file check script` |
| **Multiple independent manifests in sibling folders, no shared workspace file** | `verify no separate CI/build per folder before assuming polyrepo` |

## Audit Checklist

### Build System Health

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Build graph correctness** | the full target/task graph must resolve and build with no unbuildable, cyclic, or dangling targets before any scale optimization matters. | `Bazel`, `Buck2`, `Pants` |
| **Remote/incremental cache hit rate** | a falling hit rate usually means non-hermetic actions (embedded timestamps, absolute paths) are silently forcing full rebuilds. | `bazel-remote (self-hosted)`, `turbo --summarize`, `Nx local cache stats` |
| **Cold vs. warm build/test time at scale** | track both from-scratch and cached incremental builds as package count grows; a widening gap flags a caching or graph-partitioning regression. | `bazel --profile`, `hyperfine` |
| **Cache correctness (false hits)** | misdeclared task inputs/outputs let the cache return stale artifacts instead of rebuilding — a correctness bug, not a performance one. | `Bazel sandboxed execution`, `turbo outputs audit` |
| **Bazel-specific health** | BUILD file hygiene, strict dependency enforcement, bzlmod lockfile drift. | `Buildifier`, `strict_deps/layering_check` |
| **Nx-specific health** | project graph/config drift and distributed task execution utilization. | `nx graph`, `nx-remotecache-custom (self-hosted)`, `Nx Cloud` *(keyed)* |
| **Turborepo-specific health** | task-graph (pipeline) definition correctness and workspace pruning size. | `turbo --dry-run=json`, `turbo prune` |
| **Buck2-specific health** | configuration/target-platform correctness and custom graph tooling. | `buck2 uquery/cquery/aquery`, `BXL scripts` |
| **Pants-specific health** | dependency-inference accuracy and generated BUILD metadata freshness. | `pants dependencies`, `pants tailor --check` |

### Repo-Scale Infrastructure

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Source-control/working-copy scalability** | whether engineers can sync the repo at all past millions of files/commits via a virtual filesystem or partial clone, instead of a full local checkout. | `Scalar`, `Sapling + EdenFS`, `git --filter=blob:none` |
| **Code intelligence / cross-reference index at scale** | a maintained semantic index (jump-to-definition, find-all-usages, safe-rename impact) that stays fresh repo-wide, since grep-based navigation stops working past a certain scale. | `Kythe (self-hosted)`, `SCIP indexers`, `Universal Ctags` |

### Dependency Graph Hygiene

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Circular dependencies between internal packages** | cycles break incremental builds and independent publishing, and usually mean a missing architectural layer. | `madge --circular (JS/TS)`, `go build (Go, compiler-enforced)`, `cargo-modules --acyclic (Rust)`, `pydeps --show-cycles (Python)` |
| **Unintended cross-package coupling** | a "leaf" package quietly depending on something several layers away signals eroding architecture; track new edges added per period. | `dependency-cruiser forbidden rules (JS/TS)`, `go-arch-lint (Go)`, `cargo-modules visibility audit (Rust)`, `import-linter (Python)` |
| **Dependency graph depth and fan-out** | packages with excessive transitive depth or fan-in become de facto shared kernels that block refactors and slow affected-graph computation. | `dependency-cruiser (JS/TS)`, `godepgraph / goda (Go)`, `cargo tree (Rust)`, `pydeps (Python)` |
| **Orphaned/unused internal packages** | packages with no incoming or outgoing edges are refactor debris that still tax CI, builds, and version bumps. | `dependency-cruiser orphans rule / Knip (JS/TS)`, `deadcode (Go)`, `cargo-machete (Rust)`, `deptry (Python)` |
| **Phantom/undeclared dependencies** | code that imports a package it never declares only works because hoisting/build order hides it, then breaks on isolated builds or publish. | `depcheck (JS/TS)`, `go mod tidy (Go, compiler-enforced)`, `cargo build (Rust, compiler-enforced)`, `deptry DEP001 (Python)` |
| **Continuous CVE monitoring across all packages** | one schedule and one alert stream covers every package in the repo, instead of each package team running its own ad hoc scan (or none at all). | `Dependabot alerts (repo-wide)`, `Renovate vulnerability alerts`, `OSV-Scanner (scheduled full-repo scan)` |

### Code Ownership and Boundaries

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **CODEOWNERS coverage** | percentage of repo paths matched by at least one rule; unowned paths in a large monorepo become nobody's problem. | `codeowners-validator`, `hmarr/codeowners` |
| **CODEOWNERS/OWNERS accuracy** | owners who left the org, or teams that no longer exist, silently block required reviews or rubber-stamp without context. | `codeowners-validator`, `gh CLI org-membership script` |
| **Module/import boundary violations** | imports that cross declared architectural layers undermine the reason packages were split out. | `eslint-plugin-boundaries (JS/TS)`, `go-arch-lint (Go)`, `pub(crate) visibility (Rust)`, `import-linter (Python)` |
| **Org-wide conformance enforcement** | boundary/ownership rules published once and applied identically across every workspace, not reinvented per team. | `Bazel/Buck2 visibility`, `shared dependency-cruiser config`, `Nx Powerpack Conformance` *(keyed)* |

### CI Scaling

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Affected-only selection accuracy** | near-zero false negatives (missed impact, a safety bug) while minimizing false positives (over-triggering, a cost bug). | `Nx affected`, `turbo --filter`, `bazel-diff` |
| **CI wall-clock time trend** | track p50/p95 pipeline duration over time as package count grows, not just per-PR. | `gh run list --json`, `self-hosted Grafana/Prometheus` |
| **Flaky test quarantine process at scale** | with thousands of shared tests, one flaky test blocks every team; needs automatic detection, quarantine with owner/expiry, auto-unquarantine. | `in-repo quarantine-list convention`, `go test -count=N (Go)`, `cargo-nextest --retries (Rust)`, `pytest-flakefinder (Python)` |
| **Cost of CI compute** | compute spend per PR and per package as the repo scales, and whether caching/affected-selection is actually reducing it. | `GitHub Actions usage reports`, `BuildBuddy On-Prem (self-hosted)` |
| **Sharding/parallelism efficiency** | whether the task graph is partitioned across enough agents to keep wall-clock flat as packages are added. | `Bazel Buildfarm (self-hosted)`, `GitHub Actions matrix sharding` |
| **Trunk health gating (build-cop/sheriff rotation)** | a named rotating role plus a binary green/red tree-state signal that blocks all landing when shared trunk breaks, backed by a commit queue and auto-revert. | `GitHub Merge Queue`, `bors-ng (self-hosted)` |

### Versioning and Release Strategy

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Unified vs. independent versioning model** | one global version vs. per-package semver, applied consistently rather than ad hoc. | `Rush Version Policies (JS/TS)`, `per-module git-tag convention (Go)`, `cargo-workspaces (Rust)`, `release-please manifest mode (all languages)` |
| **Changeset/release tooling correctness** | the automated version-bump/changelog/publish pipeline must publish the right packages at the right versions, including transitive bumps. | `Changesets`, `release-please` |
| **Ability to release one package without dragging others** | a change to one leaf package shouldn't force a version bump or approval cycle on unrelated packages. | `Changesets (JS/TS)`, `independent Go module tagging`, `cargo-release (Rust)`, `release-please manifest mode (Python)` |
| **Release-graph/lockstep drift** | internal packages pinned via workspace:* must still resolve correctly once published as real semver ranges; this bug class only surfaces at publish time. | `pnpm publish --dry-run (JS/TS)`, `go list -m all post-tag check (Go)`, `cargo publish --dry-run (Rust)`, `twine check + clean-venv install (Python)` |

### Access Control

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Path-based write permissions** | restrict who can push to specific directories independent of PR review, since one repo puts every team's code under one ACL surface. | `GitHub Rulesets`, `GitLab protected branches` |
| **Approval requirements for shared/core packages** | core/foundational packages need a stricter, smaller approver set than leaf-package rules. | `CODEOWNERS`, `OWNERS files convention` |
| **Visibility as a build-time access boundary** | build-tool visibility enforces access control on internal APIs at compile time, catching what social review misses. | `Bazel visibility`, `Buck2 visibility` |
| **Break-glass path for core changes** | an audited override exists for urgent fixes to shared packages without permanently weakening standing approval rules. | `GitHub bypass list + audit log`, `GitLab push-rule exceptions` |

### Shared Tooling Consistency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Lint/format config drift across packages** | divergent ESLint/Prettier/Stylelint configs per package erode the "one repo, one standard" value proposition. | `shared eslint-config / sherif (JS/TS)`, `golangci-lint shared .golangci.yml (Go)`, `Cargo workspace.lints (Rust)`, `Ruff shared config (Python)` |
| **tsconfig/build config drift** | inconsistent compiler options or base-config extension cause type-check results to vary by package. | `shared base tsconfig.json / manypkg (JS/TS)`, `rust-toolchain.toml + workspace.package (Rust)`, `shared mypy/pyproject config (Python)` |
| **Dependency version drift** | the same third-party dependency pinned to different versions across packages causes duplicate installs, bundle bloat, version-specific bugs. | `syncpack / sherif (JS/TS)`, `go.work + go-mod-outdated (Go)`, `Cargo workspace.dependencies (Rust)`, `pip-compile shared constraints (Python)` |
| **Codegen consistency and generated-code drift** | generated clients/types must match their schema everywhere they're consumed, never hand-edited. | `buf breaking/lint`, `git diff --exit-code post-codegen` |

### Organizational Toil

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **PR queue wait time** | time from "approved" to "merged" balloons once every PR contends for the same CI capacity and merge slot. | `GitHub Merge Queue`, `gh CLI PR-timestamp export` |
| **Merge conflict rate / hot files** | a small set of frequently-touched shared files generate disproportionate conflicts; track which files these are. | `code-maat`, `git-quick-stats` |
| **Time-to-green CI** | how long a PR takes to reach a fully green run, including reruns for flakes and queueing. | `gh run list --json`, `self-hosted Grafana/Prometheus` |
| **Cost of a broad cross-package refactor** | a rename or API change touching every consumer is far more expensive at scale; size the blast radius before committing. | `nx affected / bazel query rdeps`, `ast-grep (multi-language)`, `Comby (multi-language)` |
