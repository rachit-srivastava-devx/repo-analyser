# QA / Testing Infrastructure Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| repo publishes shared test fixtures, a Playwright/Cypress config preset, or CI-template workflows consumed by *other* repos — no product/app entry point of its own | check `package.json` `main`/`exports` point at test-helper code · grep other repos' `.github/workflows` for a `uses:` reference to this one |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Meta-testing** | the framework's own core logic — matchers, runners, assertion diffing — is covered by its own test suite and ideally mutation-tested, so a bug there doesn't quietly produce false-negative results for every team relying on it downstream. | `Stryker (JS/TS)`, `gremlins (Go)`, `cargo-mutants (Rust)`, `mutmut (Python)` |
| **Flake-detector accuracy** | if this repo's job is calling other people's tests flaky, its own precision/recall is measured against a labeled ground-truth set of known-flaky and known-stable tests, not just trusted because it produces output. | `iDFlakies`, `DeFlaker`, `FlakeFlagger` |
| **Test-data generator realism** | generated synthetic fixtures are checked against real production data's statistical distributions on a recurring schedule, so the corpus doesn't quietly drift into testing scenarios nobody's real users hit. | `SDV / SDMetrics`, `Evidently AI` |
| **Cross-team adoption consistency** | every consuming team's pinned version of the shared QA tooling is tracked against the current release, instead of each team silently frozen on whatever version it first adopted. | `Backstage (self-hosted)`, `Renovate (self-hosted)` |
