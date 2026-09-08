# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-08 (~01:30am IST), by the scheduled run. Two builders in flight — see
"In-flight" below; this file will be rewritten again at the end of this run with their outcome.

Standing goal (unchanged, multi-day): implement everything in `docs/checklist-by-repo-type/`, to
find real defects per PR/repo/org. Fan out maximally, one collector per agent, builder→verifier→
merge for every change, maximize verified output. Priority order: repo-type detection →
single-repo.md → polyrepo.md → monorepo.md → everything else (pr_review.md, ai-knowledge-base.md,
ml-data-science.md, agent-skills.md, ...).

## Read this whole file before doing anything. Do not trust any other summary of prior state.

## Merged to `dev` (real, independently verified — safe to build on)

Re-verified myself via `git log --oneline` at the start of this run (2026-09-08); this list adds
three collectors that merged sometime after the 2026-09-06 handoff was written but were never
recorded here — **that gap in itself is a process miss, now closed**:

- `codeowners_health` — merge commit `bb16d47`
- `dead_code` (+ `vulture>=2.16` base dep) — merge commit `9a003f4`
- `inventory` extension (changelog/staleness) — merge commit `1e7dee1`
- `flag_debt` — merge commit `68a1206` (2026-09-06). Independently verified in a fresh worktree:
  48 scoped + 703 full-suite tests, ruff/mypy clean, `selfcheck.sh` 0 FAIL/0 warn, plus adversarial
  testing (malicious YAML RCE payload blocked, symlink loop handled, SIGKILL-mid-scan left no
  partial-write corruption, 5000-file repo in 0.18s, idempotent re-runs byte-identical).
- `license_compliance` — merge commit `4252f6e` (2026-09-06). Independently verified in a fresh
  treehouse worktree with a from-scratch venv (a pre-warmed `.venv`/`code-maat.jar` contamination
  was found and eliminated before trusting the result): 49 scoped + 608 full-suite tests, ruff/mypy
  clean. Core BSD-3-Clause hard-wrap fix reconstructed independently with a different LICENSE wrap
  point than the builder's own fixture. A real throwaway merge against `dev` (pre-merge) found zero
  conflicts; full suite against the merged tree: 752 passed, 4 pre-existing skips.
  **Follow-up in flight this run** (see below): Apache-2.0/MPL-2.0 unordered-signature-match
  false-positive in `spdx_match.py`.
- `tooling_drift` — merge commit `866a76a`. Merged between 2026-09-06 and this run; not previously
  recorded in this file. Not re-verified from scratch this run (no reason to doubt it — it's on
  `dev`, `dev`'s full suite is green, see below — but if a future run has spare capacity, a fresh
  independent re-verification of this one specifically would close the gap left by it never having
  been logged here).
- `microservices_topology` — merge commit `cce203c`. Same caveat as `tooling_drift` above.
- `agent_skill_quality` — merge commit `03f4bae` (current `dev` HEAD). Same caveat.

**Ground truth confirmed this run**: `dev` at `03f4bae`, working tree clean, full suite green —
`.venv/bin/python3 -m pytest -q` → `845 passed, 5 skipped in 26.41s`. (Must invoke pytest via the
venv's own binary, `.venv/bin/python3 -m pytest`, not a bare `python3` — each Bash tool call is a
fresh shell that doesn't retain a prior `source .venv/bin/activate`; a bare `python3 -m pytest` in
a fresh shell gives 87 false `ModuleNotFoundError` collection errors that look like a broken repo
but are just an unactivated venv. Noting this so the next run doesn't waste time re-diagnosing it.)

## Found at the start of this run: substantial uncommitted work sitting in the main `dev` checkout

At session start, `git status` on the main worktree showed **~1127 lines of uncommitted
modifications across 49 tracked files, plus an entirely new untracked `src/repo_analyser/pr_review/`
+ `tests/pr_review/` module (~1400 LOC)** — sitting directly in the main `dev` working tree, not in
any of the provisioned `worktree-agent-*` branches. This was not mentioned anywhere in the prior
version of this file. Best guess: an interactive session built this directly in the main checkout
(bypassing the worktree-per-branch convention) and never committed before running out of
time/context.

**This state was broken, not finished-but-uncommitted** — confirmed by actually running the suite
against it before touching anything: `tests/collectors/test_effort.py` failed to import
(`from repo_analyser.collectors.inventory import _gini as inventory_gini` — no such symbol exists),
which aborted test collection entirely (0 tests could run). Separately, `core/util.py`'s
`is_git_repo`/`discover_repos` had regressed the already-merged worktree-support fix (`119bc29`)
back to directory-only `.git` detection, and the corresponding test
(`test_true_for_worktree_where_dot_git_is_a_file`) had been deleted rather than updated — a real,
confirmed regression, not a stylistic difference.

**Action taken (this run, before any new work)**: rather than discard real-looking work (the
`pr_review/` module and the `write_csv()` hardening in particular read as careful, intentional
work — good docstrings, an ADR reference, a coherent design — just abandoned mid-fix) or leave it
sitting fragile as uncommitted state that a future accidental `git checkout` could destroy, it was
committed as-is (broken, documented as such) to a new branch:
**`wip/recovered-uncommitted-20260908`, commit `eeb752f`**. The main `dev` checkout was then
confirmed clean and returned to its actual HEAD (`03f4bae`) before any further work — `dev` itself
was never at risk. Full contents and the two confirmed bugs are recorded in that commit's message;
re-read it (`git show --stat eeb752f` / `git log -1 --format=%B eeb752f`) rather than trusting this
paragraph if it's more than a few days old.

## In-flight (two builders dispatched this run, in fresh worktrees, independent from each other)

1. **Fix + complete `wip/recovered-uncommitted-20260908`** (the recovered WIP above) — builder
   briefed to fix both confirmed bugs, review the `pr_review/` module and the three extended
   collectors (`e2e_quality.py`, `effort.py`, `lint_quality.py`) against `AGENTS.md`'s full bar
   (not just "does it import"), and run all three verification layers. Working in
   `.claude/worktrees/fix-wip-pr-review`. Not yet verified independently — do not merge on the
   builder's self-report alone; dispatch a fresh-worktree verifier first, per standing convention.
2. **Fix the `spdx_match.py` Apache-2.0/MPL-2.0 unordered-signature-match false-positive**
   (the follow-up filed against `license_compliance`'s merge, above) — small, isolated fix on a
   fresh branch `fix/spdx-ordered-signature-match`, working in
   `.claude/worktrees/fix-spdx-match`. Same rule: independent verifier before merge.

If this file is being read at the start of a *later* run and these are still "in-flight" with no
newer update below, treat that as a sign the run that dispatched them was interrupted — check
`git log` on both branches directly for what (if anything) actually landed, rather than assuming
either finished.

## CRITICAL — a subagent fabricated an audit this session; re-verify everything

A researcher-type subagent was asked to triage ~21 other stale `worktree-agent-*` branches against
the checklist backlog. It returned a confident, detailed table claiming ~16 of them held
substantial real work (e.g. "api_contract: new collector, 220 LOC + test", "meta_repo_health:
11-file package"), and recommended pruning only 4–5 as already-merged.

Direct verification — `git rev-list --count <merge-base-with-dev>..<branch>` run myself for all 21
branches, not delegated — proved this almost entirely false: **every one of the 21 branches has
zero commits beyond its merge-base with `dev`.** None of them contain any actual code. The only
branches with real content anywhere this session were `flag_debt` and `license_compliance`, both
handled above.

**Lesson, binding on every future run of this task, interactive or scheduled: never act on a
subagent's (or a prior doc's) claim that something "already exists", "is already merged", or has
some line count / completeness — re-verify the concrete, checkable fact yourself first** (`git log`,
`git diff --stat`, `git rev-list --count`, `wc -l`, actually reading the file). This is not
hypothetical caution: it happened, concretely, in this repo, on this date.

## Branch inventory (ground truth as of 2026-09-06 — re-verify if this file is more than a few days old)

**Confirmed-merged, already cleaned up (2026-09-06)**: `worktree-agent-a73e438fdeccf3ba2` (→
`1e7dee1`, inventory), `worktree-agent-a9ac04d5ffe5d187d` (→ `bb16d47`, codeowners_health),
`worktree-agent-a9b47d339fe98a9c1` (→ `9a003f4`, dead_code) — worktrees removed and branches
deleted. Nothing left to do here.

**Empty (zero real commits) — must be BUILT FROM SCRATCH, not rebased/fixed.** Branch existing
with a plausible name is not evidence of any work done — confirm with `git rev-list --count` before
trusting any of these have content:

| Branch | Intended capability | Checklist mapping (approx.) |
|---|---|---|
| `worktree-agent-a3995d0eb05f9b070` | api_contract (API/schema breaking-change detection) | single-repo.md § Interface & API Contract |
| `worktree-agent-a3a1dd75e1f567e87` | db_hygiene | single-repo.md § Data & Persistence Layer |
| `worktree-agent-aa143791fd521cf95` | observability | single-repo.md § Performance & Resource Efficiency |
| `worktree-agent-aead037b5c4173398` | doc_quality | single-repo.md § Design Documentation |
| `worktree-agent-a3c9b9f38b56c2b25` | e2e_quality extension | single-repo.md § Code Quality Metrics |
| `worktree-agent-aa7e609fbba76c134` | testquality extension | single-repo.md § Code Quality Metrics |
| `worktree-agent-a6b0db9f0550deefb` | lint_quality extension | single-repo.md § Code Quality Metrics |
| `worktree-agent-a9605c185393dc252` | ci_gates extension | single-repo.md § Performance Budgets |
| `worktree-agent-adfeb4b214b2709d5` | effort/churn extension | polyrepo.md § Effort Tracking |
| `worktree-agent-a90ad9c649c40894b` | deps_audit extension | polyrepo.md § Dependency Management |
| `worktree-agent-ab5386ae4a84474a0` | tooling_drift | polyrepo.md § Consistency Across Repos |
| `worktree-agent-acbb4cc822014c571` | microservices_topology | polyrepo.md/monorepo.md § Microservices Detection |
| `worktree-agent-a7ad91cff692319fa` | meta_repo_health | monorepo.md § Multi-Service Health |
| `worktree-agent-a78b28fab6d5fa882` | pr_review (**superseded** — real pr_review work now exists on `wip/recovered-uncommitted-20260908`, see above; this empty branch is redundant once that lands, safe to delete after) | pr-review.md § Automation & Gates |
| `worktree-agent-ae44ff77f5ef05440` | notebook_quality | ai-knowledge-base.md / ml-data-science.md |
| `worktree-agent-aec6e49ab900c53c7` | agent_skill_quality | agent-skills.md |
| `worktree-agent-a0778b8596908aa53` | (unknown — tip is an old dev commit, no unique work) | none found |
| `worktree-agent-af6855042a1793670` | dead_code duplicate placeholder (dead_code already merged) | none — safe to delete once confirmed empty |

None of these 18 worktrees are cleaned up. Pruning wasn't authorized beyond the 3 confirmed-merged
branches above (already done) — decide (or ask, if a live user is present) before deleting any of
these, since each is the intended home for real future work, not confirmed-dead like the 3 above.

## AGENTS.md §2.2 human-sign-off gate — status

- **api_contract's new external tool deps** (openapi/graphql/proto diff tools): **user approved
  proceeding on 2026-09-06.** Still need to: pick the specific tool(s), add to `pyproject.toml` with
  a floor-vs-exact-pin rationale comment (see `vulture`/`mutmut` for the two patterns already used),
  then actually build the collector — the approval covers the dependency, not a finished collector.
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made. If this comes up, stop and record it here rather than proceeding — do
  not assume approval carries over from the api_contract decision above.

If any *other* new external-tool-dependency or target-repo-execution need comes up that isn't
covered by an existing recorded decision in this file, **stop and record it here as blocked** rather
than proceeding — there is no live user to ask during an unattended scheduled run.

## Standing conventions (unchanged, must carry forward)

- File-size cap ~80 lines/file. One collector = one `collectors/<name>/` package, `__init__.py`
  re-exports the public API.
- Split test packages need `_<name>_helpers.py` — never a generic `_helpers.py`.
- Builder→verifier→merge, always. Every builder's self-report gets an independently-dispatched
  verifier in a **fresh** `git worktree add` (never reusing the builder's worktree/venv) before
  merge. Never merge on a builder's or a researcher-agent's self-report alone.
- CLI-wiring (`cli.py`'s `MODULES`/`run_module`, README's module table) is explicitly **not**
  required for a collector to merge — see `AGENTS.md` §9. Don't block a mergeable collector on it;
  open a tracked follow-up instead.
- Concurrency is gated by review capacity: don't fan out more new builders in one pass than can
  actually be independently verified in that same pass.
- Only merge to `dev`. Never touch `main`, never force-push, never push to `origin` without
  separate, explicit authorization.
- Attribution: git commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`; PR
  descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## Immediate next steps for whoever/whatever picks this up

1. This run's two in-flight items (above) need independent fresh-worktree verifiers, then merge to
   `dev` on genuine PASS only. If this run ends before that happens, a later run should check
   `wip/recovered-uncommitted-20260908` and `fix/spdx-ordered-signature-match` for what actually
   landed (`git log`) before assuming either is done.
2. The `CHANGELOG.md`/`docs/ROADMAP.md` sync-pass note from the prior version of this file is now
   folded into item 1 above (the recovered WIP branch already contains a doc-sync attempt for
   `flag_debt`/`license_compliance` — the builder fixing that branch should confirm it's still
   correct once `tooling_drift`/`microservices_topology`/`agent_skill_quality` are accounted for
   too, since those three are *also* undocumented in `CHANGELOG.md`/`ROADMAP.md` as of this run).
3. Once both in-flight items resolve (merged or clearly left in-flight with reasons), pick a fresh
   backlog item from the empty-branches table above (single-repo.md items first — `api_contract`,
   `db_hygiene`, `observability`, `doc_quality`), build from scratch, full builder→verifier→merge
   pipeline per `AGENTS.md` §3/§4.
4. Do not fan out builders for more than 1–2 new items per run unless verification capacity for
   that many is actually available in the same run.
5. Rewrite this file with real, git-verified state at the end of every run — no claims that
   haven't been directly checked. This run found a real instance of that rule being skipped (the
   three undocumented merges above) — don't repeat it.
