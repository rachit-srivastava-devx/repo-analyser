# Library/Package Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **package.json with main/exports/types, tagged semver releases, no Dockerfile/deploy manifests, listed on npm/PyPI/crates.io** | `npm view <name> versions`, `registry API check` |
| **pyproject.toml with [build-system], or setup.py, plus PyPI classifiers** | `pip index versions <name>` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Semver discipline / API surface diffing** | a major/minor/patch bump actually matches the real change; no breaking change smuggled in as a patch. | `cargo-semver-checks`, `api-extractor`, `apidiff (Go)`, `griffe check (Python)` |
| **Changelog accuracy vs. actual diff** | CHANGELOG entries reconcile against real merged commits/PRs since the last tag. | `Conventional Commits + commitlint`, `git-cliff` |
| **Published-artifact-vs-source drift (provenance)** | the artifact on the registry traces to an exact tagged commit built by CI, not a modified local publish. | `npm publish --provenance`, `PyPI Trusted Publishers`, `Go checksum database (sum.golang.org)` |
| **Deprecation policy & grace-period enforcement** | deprecated APIs actually warn, survive the promised number of majors, and removal PRs cite the original deprecation date. | `eslint-plugin-deprecation`, `staticcheck SA1019 (Go)`, `rustc #[deprecated] lint (Rust)`, `custom @deprecated audit script (Python)` |
| **Downstream consumer breakage risk** | who really depends on this package, and would this release break their build — tested before publish. | `npm/pnpm why`, `GitHub Dependents graph` |
| **Backward-compatibility test suite** | explicit tests pin prior-major behavior so a regression is caught pre-release rather than via a user bug report. | `Jest/Vitest pinned snapshots`, `ApprovalTests` |
| **Bundle size / tree-shakeability** | whether importing the package bloats consumer bundles, and whether unused exports can be eliminated. | `size-limit`, `Bundlephobia`, `webpack-bundle-analyzer` |
| **Package manifest correctness** | exports map, bundled types, sideEffects flag, peerDependencies ranges accurate for ESM/CJS consumers (JS/TS) — go.mod, Cargo.toml, and pyproject.toml carry the equivalent per-ecosystem correctness risk. | `publint / are-the-types-wrong (JS/TS)`, `go mod verify (Go)`, `cargo publish --dry-run (Rust)`, `twine check / validate-pyproject (Python)` |
| **Publish-path supply-chain security** | who/what can push a new version: 2FA, scoped automation tokens, no stale maintainers or lingering long-lived credentials. | `npm/PyPI Trusted Publishing (OIDC)`, `crates.io Trusted Publishing (OIDC)`, `npm audit signatures` |
| **Install-time lifecycle-script risk** | arbitrary code executing via preinstall/postinstall on every consumer's install, independent of who can publish; Python's setup.py-based sdist build carries the same risk. Go and Rust have no install-time hook (Cargo's build.rs runs arbitrary code at compile time instead — a related but distinct exposure). | `pnpm blocked-by-default scripts`, `lockfile-lint`, `prefer wheels over sdist (Python)` |
| **CI pipeline hardening of the package's own build** | maintainer CI resists workflow injection, overbroad tokens, and unpinned actions, since a compromised pipeline can forge valid provenance. | `OpenSSF Scorecard`, `zizmor`, `actionlint` |
| **Reproducible builds** | an independent third-party rebuild proves the published artifact matches source byte-for-byte, stronger than trusting signed attestation alone. | `diffoscope`, `strip-nondeterminism` |
| **Library CVE monitoring (post-publish)** | the library's own dependency tree keeps getting watched after release, not just scanned once before publish — a CVE disclosed in a transitive dependency months later should still reach the maintainer and downstream consumers. | `Dependabot security alerts (native on GitHub)`, `OSV-Scanner (scheduled re-scan)`, `GitHub Security Advisories` |
| **Typosquat/name-similarity monitoring** | watches for newly-published packages with confusingly similar names to yours — protects your users from a malicious lookalike, and flags if someone is squatting on a plausible future name. | `OSSGadget oss-find-squats`, `deps.dev name-similarity search` |
| **Peer/optional dependency range correctness** | peerDependencies ranges aren't so loose they silently accept a broken future major, nor so strict they block valid updates consumers actually need. | `npm-check-updates against peer ranges`, `manual semver-range lint script` |
| **Unpublish/yank policy** | a bad version can be marked deprecated/yanked without breaking installs already pinned to it — most registries disallow true deletion by design, so the policy has to work with that. | `npm deprecate`, `cargo yank`, `PyPI yank` |
| **Multi-registry publish consistency** | if published to more than one registry or mirror (e.g. npm plus a private mirror, or PyPI plus conda-forge), versions and checksums actually match across them instead of quietly diverging. | `checksum-diff script across registries` |
