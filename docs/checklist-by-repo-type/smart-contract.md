# Smart Contract / Blockchain Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `.sol` files, `foundry.toml`, `hardhat.config.js`/`.ts`, or `truffle-config.js` at root, with a `contracts/` directory | `find . -name "*.sol" | wc -l` · `test -f foundry.toml` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Static vulnerability scanning** | reentrancy, access-control, and unchecked-call patterns flagged before deployment, since a shipped contract is almost never patchable — every bug ships permanently. | `Slither` |
| **Invariant/property fuzzing** | properties that must hold under any sequence of calls are fuzzed automatically, going beyond example-based unit tests that only exercise the paths someone thought to write. | `Echidna`, `Foundry (invariant tests)` |
| **Formal verification of critical invariants** | the highest-value invariants (solvency, access control, no-reentrancy) are mathematically proven rather than only tested, the level of rigor now open-source and used to secure over $100B of TVL across major protocols. | `Certora Prover` |
| **Gas-cost regression tracking** | gas cost per function is snapshotted and diffed release-over-release, since gas is a cost paid by every caller forever, not an internal performance metric. | `forge snapshot` |
| **Upgrade/proxy storage-layout validation** | a proxy upgrade is checked for storage-slot collisions before deployment, since a bad layout change silently corrupts every existing user's stored state. | `OpenZeppelin Upgrades Plugins (validateUpgrade)` |
| **Compiler-version & audited-dependency pinning** | compiler version and imported library versions are pinned and reviewed against known-audited releases, since an inherited upstream bug is as permanent as one written in-house. | `manual pin review against OpenZeppelin Contracts releases` |
