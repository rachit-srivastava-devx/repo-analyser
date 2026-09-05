# Meta-Repo / Manifest Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **.gitmodules with many entries and few other source files; or manifest.xml/.repo/ (AOSP repo tool); or west.yml (Zephyr)** | `ls .gitmodules`, `cat manifest.xml` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Manifest drift/staleness detection** | the manifest's declared refs vs. what upstream repos have actually moved to; catches quietly stale tracking. | `repo diffmanifests`, `git ls-remote diff script` |
| **Pinned-commit correctness & reproducibility** | every entry resolves to an explicit immutable SHA, not a floating branch/tag. | `repo manifest -r`, `git submodule status` |
| **Submodule/subtree update lag** | commits/days each pointer sits behind upstream HEAD, surfaced as a dashboard instead of discovered at integration time. | `git submodule status`, `Renovate (self-hosted)` |
| **Broken/dangling references** | manifest points at a branch/tag/commit that's been force-pushed away or deleted, breaking sync from scratch. | `repo sync --force-sync (nightly)`, `git ls-remote --exit-code` |
| **Fresh-clone build reproducibility** | a brand-new aggregate checkout with no local cache actually builds and passes tests end to end — the meta-repo's entire reason to exist. | `GitHub Actions/GitLab CI ephemeral runners` |
| **Cross-repo compatibility of the pinned set** | the exact combination of pinned versions across sibling repos works together, not just each repo in isolation. | `West twister`, `Testcontainers` |
| **Manifest schema & remote validation** | well-formed manifest, no duplicate remotes/project names, all URLs reachable with the credentials CI actually has. | `xmllint schema check`, `West JSON-schema validation` |
| **Automated bump cadence** | manifest updates arrive via a bot on a visible, reviewable cadence rather than ad hoc manual edits that drift silently. | `Renovate (self-hosted)`, `Dependabot` |
| **Cross-repo bisectability** | binary-searching a history of pinned manifest snapshots to isolate which cross-repo commit broke something, since multi-repo history has no single total order. | `west bisect`, `custom bisect script` |
| **Round-trip baseline tracking** | bidirectional sync workflows correctly track the "already-migrated" baseline across repeated round trips so changes aren't silently duplicated or dropped. | `google/copybara`, `custom baseline-tracking file` |
