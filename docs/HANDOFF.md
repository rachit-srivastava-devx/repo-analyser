# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-08 (~23:00 IST), by the scheduled run, at its actual end. Note: real
wall-clock time this run spanned far beyond the intended 1:00am–10:00am IST window (the session's
own clock jumped from ~01:00 IST to ~22:47 IST between two consecutive tool calls with no new work
in between — likely a long idle/resume gap in the harness, not active work). No new builders were
dispatched after that gap was discovered; the two already in-flight were let finish, verified, and
resolved. **A future run should treat "started before the cutoff" builders as needing to *finish*
promptly — if a run's wall-clock spans an entire day, something outside this task's control paused
it, and whoever/whatever resumes should re-check the actual clock before doing anything new.**

## Read this whole file before doing anything. Do not trust any other summary of prior state.

## Merged to `dev` (real, independently verified — safe to build on)

Re-verified via `git log --oneline` and a real `pytest`/`ruff`/`mypy` run against `dev`'s actual
working tree at both the start and the end of this run — not copied forward from any prior file.

- `codeowners_health` — merge commit `bb16d47`
- `dead_code` (+ `vulture>=2.16` base dep) — merge commit `9a003f4`
- `inventory` extension (changelog/staleness) — merge commit `1e7dee1`
- `flag_debt` — merge commit `68a1206` (2026-09-06)
- `license_compliance` — merge commit `4252f6e` (2026-09-06). BSD-3-Clause hard-wrap fixed
  (`a237d69`). **Known false-positive NOT fixed yet** — see "Still blocked" below.
- `tooling_drift` — merge commit `866a76a`. Merged between 2026-09-06 and this run; not
  previously recorded in this file (a real process gap — see the prior version of this file, now
  superseded, for the details of how it was caught). Not re-verified from scratch by this run
  specifically (no reason to doubt it — `dev`'s full suite is green including its tests — but a
  from-scratch independent re-verification has still never been done for this one collector
  specifically; worth doing if a future run has spare capacity and wants to close that gap).
- `microservices_topology` — merge commit `cce203c`. Same caveat as `tooling_drift`.
- `agent_skill_quality` — merge commit `03f4bae`. Same caveat as `tooling_drift`.
- **`pr_review`** (new this run) — merge commit `d1a06fc`. A `pr_review/` module (merge-base
  resolution, ref verification, numstat/name-status diff parsing, added-line-range extraction,
  GitHub Actions event parsing, hunk assembly — 13 files, all ≤80 lines) answering
  `pr-review.md`'s "Automation & Gates" area, plus a hardened `write_csv()` (now requires
  `fieldnames`: a list or dataclass type, instead of silently deriving an empty header from an
  empty `rows` list) and extensions to `e2e_quality.py`/`effort.py`/`lint_quality.py`. Full history
  and context in this branch's own commits (`git log dev` around `d1a06fc`/`608ddc7`/`eeb752f`) —
  it started as uncommitted, abandoned work found sitting in the main checkout at this run's start
  (see prior version of this file for that discovery), was fixed (a real regression in
  `is_git_repo`/`discover_repos` that had undone the already-merged `119bc29` worktree-support fix
  was restored), and passed independent verification in a fresh worktree+venv before merging: 959
  passed / 10 skipped / 86% coverage, ruff/mypy clean, selfcheck 0 FAIL/1 confirmed-intentional
  warn, `pr_review`'s API run against this repo's own real git history with adversarial cases
  (swapped base/head, invalid ref, one-sided `--base`) all matching its documented contract.
  **Not wired into `cli.py`** — explicitly allowed by `AGENTS.md` §9, tracked as a follow-up below,
  not a blocker.
- The empty placeholder branch `worktree-agent-a78b28fab6d5fa882` (previously earmarked for
  `pr_review`) was confirmed still empty (`git rev-list --count <merge-base>..branch` → `0`) and
  deleted along with its worktree, now that real `pr_review` work is merged above.

**Ground truth confirmed at the end of this run**: `dev` at `d1a06fc`, working tree clean.
`.venv/bin/ruff check src/ tests/` → exit 0. `.venv/bin/mypy src/` → exit 0, 128 source files.
`.venv/bin/python3 -m pytest -q` → **964 passed, 5 skipped in 37.68s**.

**Environment note for whoever runs this next**: always invoke pytest/ruff/mypy via
`.venv/bin/python3 -m <tool>`, never a bare `python3 -m <tool>` — each Bash tool call in this
harness is a fresh shell that does not retain a prior `source .venv/bin/activate`, and a bare
invocation in an unactivated shell gives ~87 false `ModuleNotFoundError` collection errors that
look like a broken repo but are just an unactivated venv. Wasted real time on this twice across
recent runs — stop re-diagnosing it.

## Still blocked / needs real design work (not a quick follow-up)

- **`spdx_match.py`'s Apache-2.0/MPL-2.0 (and likely other shared-phrase) false-positive is NOT
  fixed.** A builder was dispatched this run (branch `fix/spdx-ordered-signature-match`, commit
  `ba6e469`, worktree `.claude/worktrees/fix-spdx-match` — left in place, not cleaned up) with an
  ordered-phrase-scan fix (phrases must appear in declared order, forward through the text).
  **Independent verification FAILED this fix**: it closes the *one* document-ordering the builder's
  own regression fixture tested, but a real, adversarially-constructed counter-example (a NOTICE
  document with a genuine MPL-2.0 license block *preceded* by an unrelated bare mention of "the
  Apache License") still misclassifies as `Apache-2.0` — confirmed at both the unit level
  (`match_spdx_id`) and the full collector level (`analyze_repo` against a real fixture repo). Root
  cause: order-only matching checks phrases appear in sequence, not that they belong to the *same*
  license fragment — it doesn't check proximity or exclusivity between different licenses' claimed
  phrase spans. **What's actually needed**: something like a proximity/window bound between a
  signature's phrases, or excluding a text span already consumed by an earlier, higher-priority
  match, or matching against license-delimited sections rather than the whole flat text — real
  design work, not a one-line patch. Also noted in passing: the fix as submitted pushed
  `spdx_match.py` to 114 lines, over `AGENTS.md` §4's ~80-line-per-file cap (was 74 before), mostly
  via a long docstring — trim this when the correctness issue is actually resolved.
  **Do not merge `fix/spdx-ordered-signature-match` as-is.** Pick this up as a real (not quick)
  backlog item, ideally with the redesign scoped out before a builder is dispatched again.
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made (unchanged from prior versions of this file).

## In-flight

None — both of this run's two builders finished, both went through independent fresh-worktree
verification, and both are now resolved (one merged, one correctly rejected and left blocked
above, not merged). Nothing left mid-verification at the end of this run.

## CRITICAL — a subagent fabricated an audit in a prior session; re-verify everything

A researcher-type subagent was once asked to triage ~21 stale `worktree-agent-*` branches against
the checklist backlog. It returned a confident, detailed table claiming ~16 of them held
substantial real work, and recommended pruning only 4–5 as already-merged. Direct verification
(`git rev-list --count <merge-base-with-dev>..<branch>`, run directly, not delegated) proved this
almost entirely false: every one of those branches had zero commits beyond its merge-base with
`dev`. This run independently re-confirmed the same discipline matters: a recovered, uncommitted
branch's *own first commit message* mischaracterized one of its two "confirmed bugs" (the
`test_effort.py` import error did not actually reproduce in the real file — see the `pr_review`
merge entry above) — caught only because the independent verifier re-read the actual file instead
of trusting the commit message's description of it.

**Lesson, binding on every future run of this task, interactive or scheduled: never act on a
subagent's (or a prior doc's, or even a git commit message's) claim that something "already
exists", "is already merged", "is broken in way X", or has some line count / completeness —
re-verify the concrete, checkable fact yourself first** (`git log`, `git diff --stat`,
`git rev-list --count`, `wc -l`, actually reading the file). This is not hypothetical caution: it
has happened, concretely, in this repo, more than once.

## Branch inventory (ground truth as of 2026-09-06 for everything below — NOT re-verified this
run beyond the two rows noted; re-verify any of these before trusting them if this file is more
than a few days old)

**Confirmed-merged, already cleaned up**: `worktree-agent-a73e438fdeccf3ba2` (→ `1e7dee1`,
inventory), `worktree-agent-a9ac04d5ffe5d187d` (→ `bb16d47`, codeowners_health),
`worktree-agent-a9b47d339fe98a9c1` (→ `9a003f4`, dead_code), `worktree-agent-a78b28fab6d5fa882`
(pr_review placeholder — confirmed still empty this run, deleted since real pr_review work is now
merged at `d1a06fc`). Nothing left to do here.

**Empty (zero real commits as of 2026-09-06) — must be BUILT FROM SCRATCH, not rebased/fixed.**
Branch existing with a plausible name is not evidence of any work done — confirm with
`git rev-list --count` before trusting any of these still have zero content (not re-checked this
run):

| Branch | Intended capability | Checklist mapping (approx.) |
|---|---|---|
| `worktree-agent-a3995d0eb05f9b070` | api_contract (API/schema breaking-change detection) | single-repo.md § Interface & API Contract |
| `worktree-agent-a3a1dd75e1f567e87` | db_hygiene | single-repo.md § Data & Persistence Layer |
| `worktree-agent-aa143791fd521cf95` | observability | single-repo.md § Performance & Resource Efficiency |
| `worktree-agent-aead037b5c4173398` | doc_quality | single-repo.md § Design Documentation |
| `worktree-agent-a3c9b9f38b56c2b25` | e2e_quality extension | single-repo.md § Code Quality Metrics (**note**: `e2e_quality.py` itself was already extended this run via the `pr_review` merge — check this branch's actual diff against what's now on `dev` before assuming it's still needed as originally scoped) |
| `worktree-agent-aa7e609fbba76c134` | testquality extension | single-repo.md § Code Quality Metrics |
| `worktree-agent-a6b0db9f0550deefb` | lint_quality extension | single-repo.md § Code Quality Metrics (**same note** — `lint_quality.py` was also extended this run) |
| `worktree-agent-a9605c185393dc252` | ci_gates extension | single-repo.md § Performance Budgets |
| `worktree-agent-adfeb4b214b2709d5` | effort/churn extension | polyrepo.md § Effort Tracking (**same note** — `effort.py` was also extended this run) |
| `worktree-agent-a90ad9c649c40894b` | deps_audit extension | polyrepo.md § Dependency Management |
| `worktree-agent-ab5386ae4a84474a0` | tooling_drift | polyrepo.md § Consistency Across Repos (**superseded** — `tooling_drift` merged at `866a76a`; this empty branch is redundant, safe to delete) |
| `worktree-agent-acbb4cc822014c571` | microservices_topology | polyrepo.md/monorepo.md § Microservices Detection (**superseded** — merged at `cce203c`; safe to delete) |
| `worktree-agent-a7ad91cff692319fa` | meta_repo_health | monorepo.md § Multi-Service Health |
| `worktree-agent-ae44ff77f5ef05440` | notebook_quality | ai-knowledge-base.md / ml-data-science.md |
| `worktree-agent-aec6e49ab900c53c7` | agent_skill_quality | agent-skills.md (**superseded** — merged at `03f4bae`; safe to delete) |
| `worktree-agent-a0778b8596908aa53` | (unknown — tip is an old dev commit, no unique work) | none found |
| `worktree-agent-af6855042a1793670` | dead_code duplicate placeholder (dead_code already merged) | none — safe to delete once confirmed empty |

The three "superseded" rows above (`ab5386ae4a84474a0`, `acbb4cc822014c571`, `aec6e49ab900c53c7`)
plus the two clearly-dead ones (`a0778b8596908aa53`, `af6855042a1793670`) were **not** deleted this
run — re-verify each is genuinely empty (`git rev-list --count`) before pruning; this file flags
them as likely-safe candidates, not as a decision already made. Everything else in the empty table
is still real, un-started work — build from scratch when picked up, don't rebase these branches.

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
  merge. Never merge on a builder's or a researcher-agent's self-report alone — this run's own
  `spdx_match.py` fix is a live example of why: the builder's numbers were all genuinely accurate,
  and the fix was still wrong.
- CLI-wiring (`cli.py`'s `MODULES`/`run_module` dict, README's module table) is explicitly **not**
  required for a collector to merge — see `AGENTS.md` §9. Don't block a mergeable collector on it;
  open a tracked follow-up instead. (`pr_review` and several others remain unwired — fine.)
- Concurrency is gated by review capacity: don't fan out more new builders in one pass than can
  actually be independently verified in that same pass.
- Only merge to `dev`. Never touch `main`, never force-push, never push to `origin` without
  separate, explicit authorization.
- Attribution: git commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`; PR
  descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## Immediate next steps for whoever/whatever picks this up

1. **`spdx_match.py`'s false-positive still needs a real fix** (see "Still blocked" above) — this
   is the most concrete, well-scoped next item, but it needs actual design thought (proximity/
   exclusivity-aware matching, or per-license-section matching) before dispatching a builder, not
   just "try again with the same approach." The existing `fix/spdx-ordered-signature-match` branch
   and its worktree are left in place for whoever picks this up to build on or reference.
2. Before picking a brand-new backlog item, spend a few minutes re-verifying the 3 "superseded"
   empty branches above (`ab5386ae4a84474a0`, `acbb4cc822014c571`, `aec6e49ab900c53c7`) and the 2
   clearly-dead ones are genuinely empty, then prune them — cheap cleanup, closes real drift in
   this file.
3. After that, pick a fresh backlog item from the empty-branches table (single-repo.md items
   first — `api_contract`, `db_hygiene`, `observability`, `doc_quality`, `meta_repo_health`,
   `notebook_quality`), build from scratch, full builder→verifier→merge pipeline per `AGENTS.md`
   §3/§4. Double-check `e2e_quality`/`lint_quality`/`effort` extension branches against what's now
   already on `dev` (this run extended all three) before assuming they're still needed as
   originally scoped.
4. Do not fan out builders for more than 1–2 new items per run unless verification capacity for
   that many is actually available in the same run.
5. Rewrite this file with real, git-verified state at the end of every run — no claims that
   haven't been directly checked. If a run's wall-clock spans an implausibly long window (see the
   top of this file), say so plainly rather than silently treating it as a normal run.
