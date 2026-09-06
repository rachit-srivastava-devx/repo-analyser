# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-06, by an interactive session, on hand-off to a scheduled daily run
(1:00am–10:00am IST, `repo-analyser-checklist-backlog`).

Standing goal (unchanged, multi-day): implement everything in `docs/checklist-by-repo-type/`, to
find real defects per PR/repo/org. Fan out maximally, one collector per agent, builder→verifier→
merge for every change, maximize verified output. Priority order: repo-type detection →
single-repo.md → polyrepo.md → monorepo.md → everything else (pr_review.md, ai-knowledge-base.md,
ml-data-science.md, agent-skills.md, ...).

## Read this whole file before doing anything. Do not trust any other summary of prior state.

## Merged to `dev` (real, independently verified — safe to build on)

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
  **Follow-up filed, not a blocker**: verifier found and reproduced a real Apache-2.0/MPL-2.0
  false-positive via unordered multi-signature matching in `spdx_match.py` — present since the
  collector's first commit (`7828e7f`), not introduced by this fix. Needs a real fix (signature
  matching should require ordered/contiguous match, not just `all(sig in text)`) — pick this up as
  a small follow-up when back in `single-repo.md`'s Code Quality / License area.

## In-flight

None as of this update — both branches that were mid-verification when this session paused
(`flag_debt`, `license_compliance`) are now merged, above.

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
| `worktree-agent-a78b28fab6d5fa882` | pr_review | pr-review.md § Automation & Gates |
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

1. `CHANGELOG.md` and `docs/ROADMAP.md` need a quick sync pass: both still describe `flag_debt` and
   `license_compliance` as in-progress/unmerged as of the last time they were edited. Fix that
   before adding new entries, so the changelog stays a reliable record.
2. Pick **one** real backlog item from the empty-branches table above (single-repo.md items first,
   e.g. `api_contract`, `db_hygiene`, `observability`, `doc_quality`), and build it from scratch —
   one collector, one builder agent, full builder→verifier→merge pipeline, per `AGENTS.md` §3
   (edge-case ladder) and §4 (design bar). The `spdx_match.py` Apache-2.0/MPL-2.0 ordered-match
   follow-up (above) is a smaller, faster pickup if a quick win is preferred first.
3. Do not fan out builders for more than 1–2 new items per run unless verification capacity for
   that many is actually available in the same run.
4. Rewrite this file with real, git-verified state at the end of every run — no claims that
   haven't been directly checked.
