# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-09 (~02:55 IST), by the scheduled run, at its actual end.

## Read this whole file before doing anything. Do not trust any other summary of prior state.

## IMPORTANT — two sessions ran on this repo concurrently tonight, undocumented

This run (the 1:00am scheduled task) discovered, part-way through, that a **second, separately
running session was actively building and merging to `dev` in real time**, starting from sometime
before this run began and continuing until roughly 02:17–02:40 IST, when it appears to have
stopped or crashed (no further commits, and a verification worktree it had just started setting up
for `monorepo_tooling` was left with only a fresh `.venv` and nothing else — no test run, no
report). That session merged **7 collectors/extensions in ~2 hours** (`api_contract`,
`migration_hygiene`, a `trivy` CI-hang fix, `notebook_quality`, `testquality` extension, `ci_gates`
extension, `observability`, `doc_quality`, `deps_audit` extension, `design_docs`) without ever
updating this file. This scheduled run independently re-verified two of the highest-risk/least-
documented items from that session (`migration_hygiene`, and the still-open `spdx_match` fix) from
scratch, and finished the one item (`monorepo_tooling`) the other session had built but not merged.

**Lesson for whoever runs this next**: if `docs/HANDOFF.md` looks stale relative to `git log
--oneline dev`, do not assume the file is merely out of date by a normal amount — check whether
another session might still be live (recent commit timestamps, worktrees with fresh `.venv`s but no
test output, `git worktree list` entries not mentioned anywhere in this file) before doing anything
that touches `dev` or this file, to avoid a collision. This run held off starting any new build work
for over 90 minutes specifically because of this.

## Merged to `dev` this run (independently verified — safe to build on)

- **`migration_hygiene`** — merge commit `8480636` (merged by the other session; independently
  re-verified from scratch by this run in a fresh worktree+venv, detached at `efc5dc7`, never
  touching `dev`/the branch myself). PASS: 1063 passed/10 skipped, ruff/mypy clean, 96-100%
  coverage per file. Adversarially rebuilt the claimed bug fix (multi-app Django false-positive
  duplicate detection) with an independently-constructed fixture — confirmed the fix is real: a
  cross-app same-numbered migration (`app1/migrations/0001_initial.py` vs
  `app2/migrations/0001_initial.py`, legitimate in Django) is no longer flagged, while a genuine
  same-app duplicate still is. Also verified graceful handling of empty repos, non-Django repos,
  committed DB files/SQL dumps via git-blob content signatures, and orphaned migrations. Not wired
  into `cli.py` — allowed per `AGENTS.md` §9, tracked as a follow-up, not a blocker.
- **`monorepo_tooling`** — merge commit `a21fd78` (completed by this run — the other session had
  built it at `27b6d3e` and started a verification worktree but never finished or merged it).
  Independently verified in a fresh worktree+venv: PASS, 1039 passed standalone with 100% coverage
  on every file in the new package, ruff/mypy clean. **The branch did not merge cleanly onto current
  `dev`** — one trivial conflict in `docs/METHODOLOGY.md` (both branches added a new `###` doc
  section at the same anchor point; zero `.py` conflicts) — resolved by concatenating both new
  sections. Re-ran the full suite after the merge commit: **1358 passed**. Detects Nx/Turborepo/
  Bazel/Buck2/Pants (any combination) via static config presence/shape only — no live build-graph
  execution (`bazel query`/`nx graph`/etc.), documented as out of scope in `docs/METHODOLOGY.md`.
  Verifier built independent fixtures for all 5 tools individually, a two-tool mid-migration repo,
  malformed configs, a 5000-file BUILD-file scan (0.25s, not pathological), and non-git/nonexistent
  paths — all handled correctly with no crashes. Not wired into `cli.py` — not a blocker.

## Merged to `dev` by the other session tonight (NOT independently re-verified by this run —
each carries only that session's own self-report; treat with the usual "verify before trusting"
discipline before building further on top of any of these)

- `api_contract` — merge commit `f92e1c8`. Static OpenAPI/GraphQL/Protobuf spec + CI breaking-
  change-tool + contract-test-tool + deprecation-marker detection. Self-reported: 1008 passed/5
  skipped, 99% coverage on the package, ruff/mypy clean. Self-reported non-blocking follow-ups: its
  own CI-tool-name detection is narrower than its docstring claims for `graphql-inspector`/
  `openapi-diff`/`swagger-diff`/`buf breaking` (name/phrase-only, no invocation-shape gating like
  `oasdiff` gets); `docs/METHODOLOGY.md` says "six known tools" where `patterns.py` defines five.
- `notebook_quality` (`e2d6e6c`), `testquality` extension (`6d215e2`), `ci_gates` extension
  (`3cddf15`), `observability` (`e5ed88c`), `doc_quality` (`1b7f613`), `deps_audit` extension
  (`ee91e79`), `design_docs` (`59fb16d`), a `trivy --skip-check-update` CI-hang fix (`f38e619`) —
  all self-reported clean by the other session's own commit/merge messages, none independently
  re-verified by this run. `observability` and `doc_quality` each note their own flat source files
  were restructured into proper `collectors/<name>/` packages mid-session to respect the ~80-line
  cap (`6c16722`, `88b09f8`) — worth a quick sanity read before extending either.

**Ground truth confirmed at the end of this run**: `dev` at `a21fd78`, working tree clean.
`.venv/bin/ruff check src/ tests/` → exit 0. `.venv/bin/mypy src/` → exit 0, 206 source files.
`.venv/bin/python3 -m pytest -q` → **1358 passed** (run directly by this session, on the actual
current tip, after the `monorepo_tooling` merge commit — not copied from any self-report).

**Environment note, still true**: always invoke pytest/ruff/mypy via `.venv/bin/python3 -m <tool>`,
never a bare `python3 -m <tool>` in an unactivated shell (each Bash tool call is a fresh shell).

## Still blocked / needs real design work (not a quick follow-up)

- **`spdx_match.py`'s Apache-2.0/MPL-2.0 false-positive is STILL NOT fixed — third attempt also
  independently verified and REJECTED this run.** Branch `fix/spdx-ordered-signature-match` now has
  3 commits: `ba6e469` (declared-order matching — verified FAILED, recorded previously), `f0d603c`
  (section-bounded phrases — never independently verified, made by the other session sometime
  before this run without any record), `084bd15` ("rank satisfiable signatures by tightest phrase
  window" — independently verified THIS run, **FAILS**). The tightest-window approach fixes the
  literal counter-example from the previous rejection but fails a structurally identical sibling:
  comparing raw character-span widths across signatures with different phrase lengths is inherently
  biased toward whichever license's signature phrases are shorter, independent of which text is the
  genuine license grant. Confirmed with an independently-built adversarial fixture (a short, natural
  sentence bare-mentioning "the Apache License" immediately followed by a genuine MPL-2.0 block —
  misclassifies as `Apache-2.0`), and confirmed this is not a one-off: the builder's own test suite
  already contains `test_bare_license_name_mention_does_not_beat_genuine_mit_text`, marked
  `@pytest.mark.xfail(strict=True)`, whose docstring self-admits the same bug class ships unfixed.
  File-size cap also still violated: now split across two files, `spdx_match.py` (97 lines) +
  `spdx_window.py` (111 lines) — worse in aggregate than the single 114-line file from attempt one.
  **Also newly discovered this run: the branch is now 27 commits stale relative to current `dev`**
  (built at `03f4bae`) and would need a rebase before any future merge attempt regardless of the
  correctness fix. **What's actually needed, unchanged from before**: a design that distinguishes a
  genuine license grant from an incidental name-drop — most likely per-license-section text
  splitting (find the boundaries of each license's own block and match within them, not comparing
  window-widths across the whole flat document) — real design work, not another proximity/window
  metric. **Do not merge `fix/spdx-ordered-signature-match` as-is; do not attempt a fourth
  window/proximity-based patch — that entire approach family has now failed three times.**
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made (unchanged for several runs now).

## In-flight

None. Every item this run touched (2 independent verifications + 1 completed merge) reached a
resolved PASS/FAIL/merged state. The other session's 9 merges from earlier tonight are also all
resolved (merged), just not independently re-verified by this run — see the section above.

## CRITICAL — re-verify everything yourself; this has burned real time more than once

Binding on every future run, interactive or scheduled: never act on a subagent's (or a prior doc's,
or a git commit message's) claim that something "already exists", "is already merged", "is broken
in way X", or has some line count/completeness — re-verify the concrete, checkable fact yourself
(`git log`, `git diff --stat`, `git rev-list --count`, `wc -l`, actually reading the file). This run
adds a new instance of the same discipline mattering: this file itself (the version at the start of
this run) was already stale by ~2.5 hours' worth of undocumented merges from a second concurrent
session before this run even started reading it — don't assume this file is current just because it
says "Last updated" recently; cross-check against `git log --oneline dev` regardless.

## Branch inventory (ground truth as of 2026-09-09 02:55 IST — checked directly this run)

**Currently existing branches**: `dev`, `main`, `fix/spdx-ordered-signature-match` (real, rejected
3x, see above — keep). That's it. Every `worktree-agent-*` placeholder branch that existed at the
start of this run has now been resolved one way or another:

- Built and merged this run or by the other session tonight: `worktree-agent-a3a1dd75e1f567e87`
  (→ migration_hygiene, `8480636`), `worktree-agent-a7ad91cff692319fa` (→ monorepo_tooling,
  `a21fd78`), `worktree-agent-a90ad9c649c40894b` (→ deps_audit extension, `ee91e79`),
  `worktree-agent-a9605c185393dc252` (→ ci_gates extension, `3cddf15`),
  `worktree-agent-aa143791fd521cf95` (→ observability, `e5ed88c`),
  `worktree-agent-aa7e609fbba76c134` (→ testquality extension, `6d215e2`),
  `worktree-agent-ae44ff77f5ef05440` (→ notebook_quality, `e2d6e6c`),
  `worktree-agent-aead037b5c4173398` (→ doc_quality/design_docs, `1b7f613`/`59fb16d`),
  `worktree-agent-a3c9b9f38b56c2b25`/`worktree-agent-a435f394ecf0e53f2`/
  `worktree-agent-a67506e510d5a7ffc` (all found to be pure ancestors of `dev` already — no unique
  content, deleted by the other session before this run got to them).
- `claude/quizzical-bun-c195e7` and `claude/sharp-meitner-c60833` — undocumented leftover branches
  from the other session (tip = the `setup.sh`/README reformat commit, already on `dev`). Both fully
  merged (ancestor-of-`dev`); this run deleted `quizzical-bun-c195e7` and its worktree.
  `sharp-meitner-c60833` was already gone by the time this run checked.
- All corresponding `.claude/worktrees/agent-*` directories for the above were removed this run
  after confirming (`git merge-base --is-ancestor`) each tip is fully subsumed by `dev`.

**Nothing left in the "empty backlog placeholder" table from prior versions of this file** — every
row was either built-and-merged tonight, or confirmed as a pure duplicate of dev history and
deleted. The backlog is NOT exhausted, though — see "Immediate next steps" below; there was simply
no leftover *placeholder branch* still sitting empty.

## AGENTS.md §2.2 human-sign-off gate — status

- **api_contract's new external tool deps**: approved 2026-09-06. The collector as merged
  (`f92e1c8`) is static-detection-only and added no new dependency, so the approved-but-unused
  budget (an actual `oasdiff`/`buf breaking`/etc. integration) is still available if anyone wants to
  build the live-execution version later — that would still need this same approval re-confirmed as
  still applicable, not re-litigated from scratch.
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made. If this comes up, stop and record it here rather than proceeding.
- No new sign-off-requiring need came up this run beyond the two already tracked above.

## Standing conventions (unchanged, must carry forward)

- File-size cap ~80 lines/file (soft target — several merged collectors sit at 85-98 lines with no
  issue; `spdx_match`'s 97+111-line split above is the kind of case that's still a real problem, not
  because of the raw number but because it's covering up a correctness gap, not just verbosity).
- One collector = one `collectors/<name>/` package, `__init__.py` re-exports only the public API.
- Split test packages need `_<name>_helpers.py` — never a generic `_helpers.py`.
- Builder→verifier→merge, always, in a **fresh** worktree the verifier creates itself (never reusing
  the builder's own worktree/venv, and — new lesson from tonight — never reusing *any* worktree of
  unclear/stale provenance either, e.g. one left by a session that may have stalled mid-run).
- CLI-wiring is explicitly **not** required for a collector to merge (`AGENTS.md` §9). Don't block a
  mergeable collector on it — open a tracked follow-up instead. Everything merged tonight remains
  unwired; that's fine and expected.
- Concurrency is gated by review capacity: don't fan out more new builders than can be independently
  verified in the same pass. Tonight's twist: also budget for the possibility that *another session
  entirely* might be consuming review capacity you don't know about — check for live/recent activity
  before assuming you have the full capacity budget to yourself.
- Only merge to `dev`. Never touch `main`, never force-push, never push to `origin`.
- Attribution: commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Immediate next steps for whoever/whatever picks this up

1. **`spdx_match` needs a fundamentally different design**, not a fourth window/proximity patch —
   see "Still blocked" above. Scope out per-license-section text splitting before dispatching a
   builder. The existing branch is also now 27 commits stale; a fresh branch off current `dev` is
   probably cleaner than rebasing the old one, given the algorithm needs to change anyway.
2. **Independently re-verify the 9 items the other session merged tonight without any independent
   verification** (`api_contract`, `notebook_quality`, `testquality` ext, `ci_gates` ext,
   `observability`, `doc_quality`, `deps_audit` ext, `design_docs`, the `trivy` fix) — not urgent
   (all self-reported clean, full suite is green including their tests), but per this repo's own
   "never merge on self-report alone" rule, none of these have actually had that independent check
   yet. Worth doing opportunistically when there's spare verification capacity and no new backlog
   item competing for it.
3. Re-scan `docs/checklist-by-repo-type/single-repo.md`'s remaining sections against what's now
   built — most sections now have at least partial coverage, but "Codebase Structure & Internal
   Modularity" (circular deps, layering/boundary enforcement, god-class detection, fan-in/fan-out —
   partially covered by the pre-existing `depgraph.py`/`flag_debt`, not fully audited this run) and
   "Compliance, Privacy & Accessibility" (GDPR/CCPA flows, a11y, audit logging — largely needs live
   execution, likely a similar sign-off-gate situation as `affected.py`) haven't been checked
   carefully. `polyrepo.md` and `monorepo.md` are in much better shape after tonight but not
   audited section-by-section either. The full `docs/checklist-by-repo-type/` directory has ~24
   files total; this project's scope per the scheduled task's own priority order only covers
   single-repo/polyrepo/monorepo/pr-review/ai-knowledge-base/ml-data-science/agent-skills — the
   backlog is **not** close to exhausted; do not consider disabling this scheduled task yet.
4. Do not fan out more than 1-2 new builders per run unless verification capacity is confirmed
   available — and confirm no other session is concurrently active first (see the top of this file).
5. Rewrite this file with real, git-verified state at the end of every run.
