# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-15 (~02:20 IST), by the scheduled run, at its actual end (well within the
1:00am-10:00am IST window this time — finished at ~02:20, no time-box issue).

## Read this whole file before doing anything. Do not trust any other summary of prior state.

This file replaces the 2026-09-14 version entirely. Everything below was personally git-verified
this run (`git log`, `git diff --stat`, `wc -l`, real command output) — nothing was copied forward
from the old file without re-checking.

## A research-agent fabrication was caught and corrected mid-run — read this before trusting any
future research pass

A researcher agent was dispatched to audit `polyrepo.md`/`monorepo.md` for genuine collector gaps.
Its top-ranked candidate ("Fleet-wide Lint/Format Config Drift", cited as fully uncovered) was
**wrong** — `collectors/tooling_drift/` already did lint/format config-drift detection, confirmed
by a 30-second `grep` the moment its report came back. The researcher had grepped for the checklist
wording but never actually found or read the existing `tooling_drift/` package. This is not the
first fabrication incident in this project (see the 2026-09-06 stale-branches incident referenced
in this file's own template) — it's the second, and it happened on a *research* task, not a build
or verify task, which the standing "never trust a subagent's completeness claim" rule doesn't
explicitly call out as a risk category. **Extending the rule explicitly: research-agent "this is
uncovered" claims need the same treatment as "this already exists" claims — grep for the obvious
keyword yourself before acting on a reported gap, not just before acting on a reported completion.**
Once corrected, the *real* gap turned out to be narrower and more precise than the researcher's
framing: `tooling_drift`'s existing dimensions (lint-config drift AND dependency-version drift) both
only compared manifests **within one repo's tree** (monorepo-scoped) — the polyrepo-scoped
(cross-repo) variant of both was genuinely uncovered, and both got built and merged this run (see
below).

## Merged to `dev` this run (all independently verified in a fresh worktree — safe to build on)

- **`deps_audit.py` docstring/test fix** — commit `3ab8c6d`. Independent re-verification (first
  since the `ee91e79` merge on 2026-09-09) found the whole extension **PASS** — real
  license-checker/pip-licenses/go-licenses runs against real fixtures all reproduced exactly as
  documented, including the go-licenses crash correctly surfacing as `ToolExecutionError`, not
  swallowed. One defect found: the docstring's "confirmed live: `idna` -> `BSD-3-Clause`, already
  exact" claim does not reproduce — real `idna` reports `"BSD License"` (bare, ambiguous), which the
  code already correctly leaves unmapped and flags as a violation. The underlying logic was never
  wrong, only this one illustrative claim (and the matching test comment/fixture, which used `idna`
  as a stand-in for a case it doesn't actually represent). Fixed directly (doc + test rename to a
  synthetic package name), not routed through builder/verifier since it was a pure prose correction
  found during verification, matching this file's own established precedent (`033dfba`, `f752e99`).
- **`supply_chain.py` trivy silent-failure fix** — merge commit `a5ddf30` (fix commit `0f4cf99`).
  Independent re-verification of the original `--skip-check-update` fix (`f38e619`, merged
  2026-09-09, never re-checked until now) found: (a) the ORIGINAL merge commit's self-reported pytest
  count and CLI timing both fail to reproduce (claimed 1008 passed/36s; real numbers were
  1063 passed/1.03s at that exact commit) — a third fabrication data point for this project, this
  time inside a commit message rather than an agent report, so **treat old commit-message
  self-reports with the same skepticism as agent self-reports going forward**; and (b) a real,
  previously-undisclosed bug in the exact function the original fix touched: `_trivy_config_repo`/
  `_trivy_sbom_repo` silently returned an empty/clean result whenever trivy crashed before writing
  its output file (any non-timeout failure), making a tool crash indistinguishable from a genuinely
  clean scan — a direct violation of ADR-0001. **Fixed and independently re-verified PASS**: both
  functions now raise `ToolExecutionError` when trivy exits non-zero and never wrote a report; the
  legitimate exit-0/no-findings case is unchanged. Two new regression tests, proven real via
  revert-and-check. One minor accepted process note from the verifier: the fix's one-sentence
  `docs/METHODOLOGY.md` addition is adjacent scope (about the older `--skip-check-update` test's own
  blind spot) rather than strictly about this fix — harmless, accurate, not reverted.
- **`tooling_drift` cross-repo lint/format config drift** — merge commit `3c90286` (feature commit
  `3fd4134`). New third dimension in the existing `collectors/tooling_drift/` package (NOT a new
  collector — same measured dimension, "does this repo's lint/format config match X", with X now
  "the portfolio's canonical config" instead of "this repo's own sibling directories"). Reuses
  `lint_configs.py`'s existing `eslint_display`/`ruff_display`/`golangci_display` fingerprint
  functions unchanged. Compares each repo's ROOT-level manifest only. Majority/canonical vote per
  kind (eslint/ruff/golangci), with a documented lexicographic tie-break, "missing config" allowed to
  itself be the canonical value, symlink/duplicate-repo dedup by resolved real path, and the whole
  dimension skipped (not silently absent) for a single-repo or empty portfolio. Output reuses the
  existing `ToolingDriftRow`/`tooling_drift.csv` shape (`config_kind="cross_repo_eslint"` etc., one
  row per drifted repo) plus a new `cross_repo_canonical` section in `tooling_drift_summary.json`.
  Independently verified PASS against fresh, independently-built fixtures (not the builder's own):
  majority vote, tie-break, dedup, and missing-as-canonical all confirmed in both directions; two
  implementation details confirmed load-bearing via break-and-check (dedup, tie-break); 500-repo
  synthetic stress ran in 47ms with correct output; full suite green (pass/skip split differs only by
  which optional external tools are installed per machine — total collected identical, not a
  fabrication, and now an established, expected pattern across this run's several independent
  verifications).
- **`tooling_drift` cross-repo dependency-version drift** — merge commit `12312b2` (feature commit
  `c9b6fe2`). Fourth dimension in the same package, answering the polyrepo-scoped sibling of the
  above. Reuses the existing generic `dependency_drift()` function completely unchanged (verified via
  empty `git diff` on that file) — only the input now spans every repo's root manifest across the
  whole portfolio instead of one repo's sibling manifests. **Row-shape decision, worth reading if you
  touch this again**: unlike a config fork (naturally "one repo's" finding), a drifted dependency
  name inherently spans multiple repos at once, so this dimension deliberately does NOT reuse
  `ToolingDriftRow`'s per-repo grain — it writes a separate CSV artifact
  (`tooling_drift_cross_repo_deps.csv`: `dependency_name, ecosystem, versions_found, repos_by_version,
  repo_count`) rather than force-fitting a shape that doesn't match, per `AGENTS.md` §4's "don't
  average two different things into one shape to look tidier." No cap on how many drifted
  dependencies get reported (honest, not silently truncated — could get verbose on a huge portfolio
  with many shared libraries, disclosed not fixed). Independently verified PASS with independently-
  built fixtures: majority/threshold/dedup/ecosystem-isolation/empty-and-single-repo-skip all
  reproduced; two implementation details confirmed load-bearing via break-and-check (repo dedup,
  >=2-repos threshold); CSV/summary row-count agreement verified at every fixture size; linear scaling
  confirmed at 150/600 synthetic repos (0.163s/0.785s, ~4.8x for 4x repos). One pre-existing,
  undisclosed limitation surfaced (inherited from `dependency_drift()`, already shipped on `dev`
  before this run, not introduced by this change): version strings are compared as raw text, so
  `"^1.2.3"` vs `"1.2.3"` would register as drift even though it might not be semantically real —
  worth a `docs/METHODOLOGY.md` note next time this area is touched, not urgent.

## Original 9-item re-verification backlog — now fully closed

The 2026-09-09 run flagged 9 previously-merged items as "never independently checked." As of
yesterday's run, 7 were done. **This run closed the last 2**: `deps_audit` (PASS, doc fix above) and
the `trivy --skip-check-update` fix (FAIL → fixed → PASS, above). All 9 are now independently
verified at least once. This checklist item from `docs/HANDOFF.md`'s own "immediate next steps" is
retired — don't carry it forward.

## Branch inventory (ground truth as of 2026-09-15 ~02:20 IST — checked directly this run)

**Currently existing branches**: `dev`, `main`. `git branch -a` confirms — nothing else, local or
remote-tracked-only-in-name. Every branch and worktree created by this run's own agents (2 builders,
4 verifiers, 1 researcher) was merged-then-deleted or removed read-only, each confirmed via
`git merge-base --is-ancestor <tip> dev` before deletion: `fix/trivy-config-silent-failure`,
`cross-repo-tooling-drift`, `feat/cross-repo-dependency-version-drift`, plus every verifier's own
disposable worktree. `git worktree list` shows only the main repo worktree — no stray
`repo-analyser-worktree*` or `repo-analyser-worktrees/*` directories remain.

## AGENTS.md §2.2 / §8 human sign-off gate — status

- No genuinely new sign-off-requiring need came up this run. No new external tool dependency was
  added (all 4 changes reused existing tools/functions). No target-repo build/test execution was
  needed for anything built or fixed this run.
- **`api_contract`'s approved-but-unused live-execution budget** (approved 2026-09-06, still
  unused): unchanged, still available if anyone wants to build the live `oasdiff`/`buf breaking`
  integration later.
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made, unchanged for several runs now.

## Ground truth confirmed at the end of this run

`dev` at `12312b2`, working tree clean. `.venv/bin/ruff check src/ tests/` → exit 0.
`.venv/bin/mypy src/` → exit 0, 230 source files. `.venv/bin/python3 -m pytest -q` →
**1505 passed, 14 skipped, 2 xfailed** (run directly by this session on the actual current tip). The
2 xfails are unchanged from prior runs, both honestly-documented residual limitations (license
compliance, ci_gates) — not silent bugs.

**Collector inventory**: 18 package-style collectors under `collectors/<name>/` (including
`tooling_drift`, now with 4 dimensions instead of 2 — see above), 18 flat-file collectors still under
`collectors/*.py` directly (unchanged this run: `ci_gates.py` at 387 lines, `testquality.py` at
583 lines — both still real file-size-convention debt, still someone else's follow-up).

**Environment note, still true**: always invoke pytest/ruff/mypy via `.venv/bin/python3 -m <tool>`,
never a bare `python3 -m <tool>` in an unactivated shell (each Bash tool call is a fresh shell). Also
now confirmed across 4 independent verifications this run: pass/skip split legitimately varies by
machine depending on which optional external tools (java/node/semgrep/gitleaks/osv-scanner/jscpd/
staticcheck/mutmut/`tools/code-maat.jar`) are installed — always check the TOTAL collected count
matches before calling a discrepancy a red flag, don't just compare pass counts.

## Standing conventions (unchanged, must carry forward)

- File-size cap ~80 lines/file (soft target). `ci_gates.py` (387) and `testquality.py` (583) remain
  real, tracked debt — not touched this run, no worse either.
- One collector = one `collectors/<name>/` package, `__init__.py` re-exports only the public API. A
  new comparison AXIS on an already-owned measured dimension (this run's two cross-repo extensions)
  belongs inside that dimension's existing package, not as a new collector — see `AGENTS.md` §4's
  "one collector = one measured dimension" test and this run's own reasoning above.
- When a new dimension's natural output doesn't fit an existing CSV's row grain, write a new,
  separate, clearly-named artifact rather than force-fitting the old shape — this run's cross-repo
  dependency-drift is now the second precedent for this (`AGENTS.md` §4 already had the
  jscpd-vs-sha256-duplication precedent; this is the same principle applied to a new case).
- Split test packages need `_<name>_helpers.py` — never a generic `_helpers.py`.
- Builder→verifier→merge, always, in a **fresh** worktree the verifier creates itself, with its own
  fixtures (not the builder's). This run's practice: every verifier this run built its OWN throwaway
  git repos rather than reusing the builder's, specifically so a builder's fixture couldn't hide a
  bug the builder had unconsciously designed around — worth keeping as explicit instruction text in
  every future verifier dispatch, not just implied.
- A builder or research agent's "this is uncovered" / "this already works" claim is unverified until
  a human/agent re-derives the concrete fact (grep, `git diff --stat`, real command output) — this
  run added a THIRD data point (the tooling_drift research miss) to the two already on record
  (2026-09-06 stale-branches fabrication, 2026-09-09/14's trivy self-report timing/count mismatch).
  Treat this as a settled pattern, not a one-off: verify every "already exists" AND every "doesn't
  exist" claim before acting on it, from any source (subagent report or old commit message alike).
- CLI-wiring is explicitly **not** required for a collector/dimension to merge (`AGENTS.md` §9).
  `tooling_drift` remains fully unwired from `cli.py`'s `MODULES` dict after 4 dimensions now — still
  not a blocker, still real follow-up work, still not silently dropped (noted here every time).
- Only merge to `dev`. Never touch `main`, never force-push, never push to `origin`.
- Attribution: commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Immediate next steps for whoever/whatever picks this up

1. **`tooling_drift` CLI wiring** — 4 real dimensions now live in this package and none of them are
   reachable via `python3 -m repo_analyser analyze --modules tooling_drift`. Low-risk, well-scoped,
   pure plumbing (add to `cli.py`'s `MODULES` dict, README's module table) — a good "first thing
   tomorrow" item precisely because it needs no new design judgment, just wiring already-correct code
   in. Verify the CLI run's CSV/JSON output matches what this run's direct-call verifications already
   confirmed.
2. **Flaky-test quarantine/tracking** — confirmed via a precise `grep -rlwi` this run (not just the
   researcher's original claim) to be genuinely uncovered anywhere in `collectors/`. Real gap, but
   **more design-ambiguous than either cross-repo extension built this run** — test-quarantine
   patterns and file conventions vary by language/framework/test-runner, unlike lint-config
   fingerprinting or dependency-version strings which have one obvious representation. Deliberately
   NOT started this run to avoid a rushed, under-designed first pass late in a long session — pick
   this up with a full run's budget, not a squeezed one. Do the contract/edge-case-ladder walk (§3)
   extra carefully before writing code: decide up front what counts as "quarantined" (a naming
   convention? a separate config file? both, and do they ever disagree?) for each of Python/JS/Go
   before touching any code.
3. **Re-scan `polyrepo.md`/`monorepo.md` once more, properly this time** — this run's researcher
   agent's coverage claims for these two files should be treated as unverified/partially wrong (see
   the fabrication note above) beyond the two items this run actually confirmed and fixed
   (cross-repo lint + dependency drift). Its other 3 ranked candidates (repo lifecycle/sprawl
   labeling, flaky-test quarantine, build-tool/Dockerfile/Makefile config consistency) were
   spot-checked briefly this run: repo lifecycle staleness banding turned out to ALREADY be
   substantially covered by `inventory/staleness_band.py` (fresh/aging/stale/abandoned bands,
   confirmed by reading the file) — so that candidate is mostly not a real gap, though a literal
   "tagged experimental/production/deprecated" metadata field is a separate, thinner, probably-not-
   worth-it question. Build-tool/Dockerfile/Makefile consistency across a portfolio was NOT
   conclusively checked either way this run (real `grep` hits exist in `depgraph.py`/`ontology.py`/
   `supply_chain.py`/`repo_type/*` for Dockerfile-adjacent terms, but whether any of them actually do
   cross-repo *consistency comparison* rather than per-repo detection was not read closely) — read
   those files before either building or discarding that candidate.
4. **`testquality.py`'s package restructuring** (580+ lines) and wiring its 3 static signals into
   `deep_reports.py`/`per_repo_digest.py` — still not done, unchanged for several runs, still real,
   still lower priority than the above.
5. **`docs/METHODOLOGY.md` gaps worth a follow-up note, not urgent**: `tooling_drift`'s
   dependency-version comparison (both the pre-existing within-repo dimension and this run's new
   cross-repo one) compares version strings as raw text with no normalization — `"^1.2.3"` vs
   `"1.2.3"` registers as drift. Not touched this run since it's pre-existing behavior on the
   within-repo side, not a regression, but worth disclosing in the docs the next time this area is
   touched.
6. Rewrite this file with real, git-verified state at the end of every run. Keep flagging fabrication
   incidents here when caught — this file is now the institutional memory for "why we don't trust
   subagent completeness claims," and it's earned that role three separate times.
