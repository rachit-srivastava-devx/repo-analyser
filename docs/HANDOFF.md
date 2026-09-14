# Handoff — checklist-by-repo-type backlog

Last updated: 2026-09-14 (~12:50 IST), by the scheduled run, at its actual end (ran well past the
intended 1:00am-10:00am IST window — see "Anomaly this run" below).

## Read this whole file before doing anything. Do not trust any other summary of prior state.

This file replaces the 2026-09-09 version entirely. Everything below was personally git-verified
this run (`git log`, `git rev-list --count`, `git diff --stat`, real command output) — nothing was
copied forward from the old file without re-checking.

## Anomaly this run — a single verification agent ran ~10.4 hours wall-clock

The independent re-verification of the `testquality` extension (dispatched ~02:52 IST) did not
return until ~12:49 IST — its own `duration_ms` was `37,590,267` (~10.4 hours), far outside every
other agent this run (15-60 minutes each). This blew the intended 1:00am-10:00am IST working window
by ~2.8 hours and meant the run could not fix-and-reverify that FAIL within-run as it otherwise
would have (the "no new builder dispatch after ~8:00-8:30am" rule was already in effect by the time
the result came back). **Flagging for whoever schedules/monitors future runs**: if a single
dispatched agent runs this long again, it's worth investigating whether something hung (an
unresponsive subprocess, a retry loop) rather than assuming it's normal verification depth — this
run has no way to know which it was, since the result that came back was coherent and well-evidenced,
not garbage. No other anomaly (no evidence of a second concurrent session this time; `git worktree
list`, `git reflog`, and commit timestamps were all consistent with this run's own actions).

## Merged to `dev` this run (independently verified — safe to build on)

- **`debt_markers`** — new collector, merge commit `f908667`. Answers single-repo.md's
  "Tech debt backlog size & age" row: TODO/FIXME/HACK/XXX/BUG marker count + git-blame-derived age,
  pure git+regex, no new external tool. **Went through 2 verification rounds**: round 1 FAILED on 3
  real defects (a multi-line Python triple-quoted string false-positive contradicting the module's
  own docstring claim; an uncaught `UnicodeDecodeError` crash on a commit with invalid-UTF8 author
  bytes, killing the whole portfolio run; and the original builder's own "0 markers in this repo's
  own tree, cross-checked via git grep" claim didn't reproduce — real count was 2, and the verifier's
  `git grep -E '\bTODO\b'` cross-check tool itself doesn't honor `\b` on this platform's git 2.51.0).
  All 3 fixed on the same branch (commit `9bc1a45`), each with a regression test proven via
  revert-and-check (test fails pre-fix, passes post-fix). Round 2 (fresh worktree, brand-new
  fixtures, not reused from round 1) — **PASS**: 100% coverage on every file in the package, all
  previously-passing behavior (batching, git-mv rename handling, staged-only markers, submodule
  paths) spot-checked and still correct. Not wired into `cli.py` — allowed per `AGENTS.md` §9, not
  a blocker.
- **`ci_gates` lockfile-verification fix** — fix-forward to an already-shipped extension (original
  extension was `3cddf15`, merged before this run started), merge commit `9221e9a`. **Went through
  4 verification rounds**, each finding a real, different problem, each fixed before the next round:
  1. Original extension had 2 real bugs: an `echo "npm ci"`-style string was wrongly counted as a
     real invocation (false positive), and a monorepo with mixed npm/poetry compliance collapsed to
     one misleading repo-wide boolean (conflation, violating `AGENTS.md` §4's "don't average two
     different measurements" rule). Fixed with quoted/commented-text stripping + per-manager
     attribution (`lockfile_managers_found`/`lockfile_managers_verified_in_ci`).
  2. That fix's first draft **removed** the already-shipped `lockfile_verified_in_ci` CSV column —
     a breaking format change `AGENTS.md` §8/§10 requires human sign-off for, which nobody could give
     in an unattended run. Resolved by making the fix purely additive: `lockfile_verified_in_ci`
     restored as a derived "any manager verified" aggregate, both old and new columns coexist.
  3. The quote-stripping regex from fix #1 let an unbalanced single quote (a plain English
     contraction like "Don't" in an echoed string) span across newlines and silently swallow a real
     `npm ci` step later in the same block — a new, undisclosed silent-false-negative regression.
     Fixed by excluding `\n` from the regex's character classes.
  4. That fix in turn made a **genuine multi-line quoted string** (real, valid bash — e.g. a
     multi-line `echo "..."` release-notes message) get checked line-by-line instead of as one span,
     so command-shaped text *inside* a real quoted string could be wrongly counted as a real
     invocation — a new false positive, symmetric to the false negative fixed in step 3. **This
     round-trip (fix A causes bug B, fix B causes bug A's sibling) is structurally identical to this
     repo's own `spdx_match.py` precedent** (3 failed window/proximity patches, documented in this
     file's 2026-09-09 version) — so rather than attempt a 5th regex patch on the same heuristic-
     approach family, the decision was made to keep the round-3 fix as-is and honestly document the
     residual limitation instead: an inaccurate in-code comment claiming "quotes are always
     single-line in every shell dialect" was corrected, the limitation was written into
     `docs/METHODOLOGY.md` symmetrically next to the already-disclosed `bash -c "npm ci"`
     false-negative gap, and an `@pytest.mark.xfail(strict=True)` regression test documents it
     (following `test_spdx_match.py`'s own established convention for this exact situation).
  Round 4 (final) verification confirmed: all 3 original bugs still fixed, the xfail is genuine
  (not silently passing), the disclosed limitation is accurate (independently reproduced), no scope
  creep (diff touches only `ci_gates.py`/its tests/`docs/METHODOLOGY.md`), and no downstream
  consumer reads the affected columns today. **PASS, merged.**

## Independently re-verified this run (from the 9 items the 2026-09-09 run's HANDOFF flagged as
"merged by another session, never independently checked")

- **`api_contract`** — **PASS**. Both of its own self-reported follow-ups confirmed real (CI-tool
  detection narrower than docstring claims; METHODOLOGY.md said "six known tools" where
  `patterns.py` defines five). Found and fixed one more, undisclosed: README claimed `.changeset/`
  semver-discipline detection with zero corresponding code anywhere in the package (confirmed by
  grep and a real fixture — identical output whether `.changeset/` present or absent). Fixed in
  commit `033dfba` (README + METHODOLOGY.md + a stale "schema_kind enum" docstring reference that
  doesn't exist in the code — all doc-only, no code defect).
- **`observability`** — **PASS**, clean. 22 independently-built adversarial fixtures across all 4
  signals (structured logging, metrics, tracing, k8s probes) all behaved exactly as documented; the
  "presence not usage" limitation is honestly disclosed in-code, not oversold in README. Only gap:
  `docs/METHODOLOGY.md` has zero section for this collector at all (unlike siblings merged the same
  session) — noted as a follow-up, not fixed this run.
- **`doc_quality`** — **PASS**, clean. `interrogate` dependency registration confirmed real and
  correctly wired through `core.util.run()`. Coverage-percentage cross-checked exactly against
  interrogate's own CLI output on a hand-built fixture. Every edge-case-ladder rung (missing tool,
  no tags, malformed encoding, unsupported language, tool crash) degrades honestly. No code defect
  found.
- **`notebook_quality`** — **PASS**. 21/21 independently-built adversarial fixtures passed (real
  uncleared-output detection, non-linear execution-count detection including the null-`execution_count`
  edge case, secret-pattern false-positive avoidance, malformed/ancient-nbformat handling). Found the
  merge commit's own self-report overstated "huge notebooks covered" (zero large-notebook test existed
  in the merged suite, though the underlying code does handle it correctly and fast — 0.28s at
  ~200MB). Found and fixed one stale-doc issue: `docs/ROADMAP.md`'s planned column list predated the
  shipped `notebooks_unparseable` field. Fixed in commit `f752e99` (doc-only).
- **`design_docs`** — **FAIL → resolved as doc-only fix, commit `7ea9364`.** The collector's actual
  logic (including the `533c3b2` rename-tracking fix, reproduced against raw `git log --follow
  --reverse` ground truth) is correct — every adversarial fixture behaved right. But README claimed
  C4/Structurizr/PlantUML diagram detection with **zero** corresponding code anywhere in the package
  (confirmed by grep and a fixture: a repo with only a genuine `.dsl`+`.puml` pair produced
  byte-identical output to one with no architecture docs at all) — same defect class as
  `api_contract`'s `.changeset/` claim. Fixed: removed the false claim from README, and added two
  further undisclosed-but-real limitations found the same pass to `docs/METHODOLOGY.md`: HLD/ADR/
  runbook checks are root-scoped only (a monorepo's subpackage-local docs are silently invisible),
  and `tally_adrs` runs one `git log --follow` subprocess per accepted ADR with no batching (~75s at
  3000 ADRs in one repo, real but bounded).
- **`ci_gates` extension** — **FAIL, then fixed and re-verified PASS** — see "Merged to `dev` this
  run" above for the full 4-round story.
- **`testquality` extension** — **FAIL, NOT fixed this run** (verification result arrived after the
  time-box for new builder dispatch had passed — see "Anomaly this run" and "Still blocked" below).

## Still not independently re-verified (2 of the original 9 remain)

- **`deps_audit` extension** (license-compliance column + Python/Go staleness parity, `ee91e79`) —
  not touched this run. Next run: pick this up if capacity allows.
- **`trivy --skip-check-update` CI-hang fix** (`f38e619`) — not touched this run. Lower priority
  than a collector re-verification (it's a config-flag fix, not new detection logic), but still
  technically unverified per this repo's own "never trust self-report" rule.

## Still blocked / needs real work (not a quick follow-up)

- **`spdx_match.py`'s Apache-2.0/MPL-2.0 false-positive** — per the 2026-09-09 HANDOFF and this
  run's independent confirmation (full test suite run, ground truth checked): this was picked up and
  substantially improved by a human (merge `5b61c2c`, 2026-09-09 08:34 IST, well after the prior
  scheduled run's own rejection at ~03:00 IST that same morning — a real person came back and merged
  it, overriding the prior run's "do not merge as-is" recommendation). Current state, personally
  verified this run: **1 xfail remains** (`test_bare_license_name_mention_does_not_beat_genuine_mit_text`
  or its current equivalent — a documented, honestly-marked residual limitation, not a silent bug),
  full suite green. This is now in a stable, honestly-documented state — **not** still "blocked" the
  way the 2026-09-09 file described; downgrading this from "still blocked" to "stable, 1 known
  documented limitation, no action needed" based on direct verification, not on the old file's word.
- **`affected.py`'s need to execute the target repo's own build** — still fully open, no branch
  exists, no decision made (unchanged for several runs now).

## In-flight

None. `testquality`'s Python/JS fuzz-detection proxy-for-the-property defect (found FAIL by this
run's own scheduled pass, documented above as blocked at the time) was fixed and merged
interactively afterward — merge commit `2602229` on top of `f752e99`+ (`46fc672`, fix branch
`fix/testquality-fuzz-usage-detection`). Independently re-verified PASS in a fresh worktree before
merge: the specific defect (declared-but-unused dependency reporting identically to real usage) is
reproduced-then-fixed 4 independent ways, Go's branch confirmed unchanged/correct, no CSV shape
change. One non-blocking gap disclosed, not yet fixed: none of the three fuzz-usage regexes are
comment-aware (a commented-out `@given(...)`/`.assert(`/`func Fuzz...` still matches) — confirmed
symmetric across all three ecosystems including the untouched Go path, so it's a pre-existing
limitation of the whole regex-text-match technique, not a regression. Worth a follow-up note in
`docs/METHODOLOGY.md`'s fuzz-signal bullet, not urgent.

Remaining lower-priority items from that same verification, still not done (unchanged from before):
`testquality.py` is still a 580+-line flat file, never restructured into a package; its 3 new
signals (`pyramid_*`/`has_fuzz_tests`/`snapshot_*`) are still not wired into
`deep_reports.py`/`per_repo_digest.py`/`exec_deck.py` (dead CSV-only output, not a correctness bug).

## Branch inventory (ground truth as of 2026-09-14 ~12:50 IST — checked directly this run)

**Currently existing branches**: `dev`, `main`. That's it — `git branch -a` confirms. Every
worktree and branch created by this run's own agents (builders and verifiers, ~14 dispatched total)
was cleaned up after confirming `git merge-base --is-ancestor <tip> dev` for each: `debt_markers`'s
2 branches, `ci_gates`'s fix branch plus every verifier's own branch/worktree across all 4 rounds,
and every read-only verifier worktree for `api_contract`/`observability`/`doc_quality`/
`notebook_quality`/`design_docs`/`testquality`. `git worktree list` shows only the main repo
worktree; no stray `.claude/worktrees/agent-*` directories or `/private/tmp/verifier-worktrees/*`
paths remain.

## AGENTS.md §2.2 / §8 human sign-off gate — status

- No genuinely new sign-off-requiring need came up this run. The `ci_gates` fix's CSV-column removal
  was caught and resolved (made additive) rather than requiring an ask — see the 4-round story above.
- **`api_contract`'s approved-but-unused live-execution budget** (approved 2026-09-06, still
  unused): unchanged, still available if anyone wants to build the live `oasdiff`/`buf breaking`
  integration later.
- **`affected.py`'s need to execute the target repo's own build**: still fully open, no branch
  exists, no decision made. If this comes up, stop and record it here rather than proceeding.

## Ground truth confirmed at the end of this run

`dev` at `2602229`, working tree clean. `.venv/bin/ruff check src/ tests/` → exit 0.
`.venv/bin/mypy src/` → exit 0, 224 source files. `.venv/bin/python3 -m pytest -q` →
**1484 passed, 14 skipped, 2 xfailed** (run directly by this session, on the actual current tip, not
copied from any self-report). The 2 xfails are both honestly-documented residual limitations (one in
`license_compliance` from the prior spdx_match work, one in `ci_gates` from this run's own 4-round
fix) — not silent bugs. (The scheduled portion of this run ended at `9221e9a`/1479-passed; the
`testquality` fuzz-detection fix — see "In-flight" above — was completed interactively afterward and
is included in this final count.)

**Collector inventory** (for orientation, not exhaustive): 18 package-style collectors under
`collectors/<name>/` (including this run's new `debt_markers`), 18 flat-file collectors still under
`collectors/*.py` directly (including `ci_gates.py`, now 387 lines post-fix, and `testquality.py` at
583 lines — both real file-size-convention debt, `testquality`'s already flagged above as a
follow-up).

**Environment note, still true**: always invoke pytest/ruff/mypy via `.venv/bin/python3 -m <tool>`,
never a bare `python3 -m <tool>` in an unactivated shell (each Bash tool call is a fresh shell).

## Standing conventions (unchanged, must carry forward)

- File-size cap ~80 lines/file (soft target). `ci_gates.py` (387 lines) and `testquality.py`
  (583 lines) are both real, tracked debt against this convention — not this run's to fully resolve,
  but don't make either worse without at least a documented reason.
- One collector = one `collectors/<name>/` package, `__init__.py` re-exports only the public API.
- Split test packages need `_<name>_helpers.py` — never a generic `_helpers.py`. (Note: this run
  confirmed `AGENTS.md`'s own claim that "nothing under `tests/` has an `__init__.py` anywhere" is
  now stale — at least 11 collectors' test packages have an empty `__init__.py`, an established
  precedent, not a defect when found in a new PR.)
- Builder→verifier→merge, always, in a **fresh** worktree the verifier creates itself. This run's
  `ci_gates` saga is the clearest evidence yet for why: 4 rounds, each catching something the
  previous round's fix introduced — skipping any single round would have shipped a real regression.
- CLI-wiring is explicitly **not** required for a collector to merge (`AGENTS.md` §9).
- A CSV column removal on an already-shipped collector is a **stop-and-flag** situation, not
  something to route around — this run hit it once (`ci_gates`) and resolved it by making the fix
  additive rather than either blocking indefinitely or silently breaking the format.
- When a fix-for-a-fix starts oscillating between two failure modes (fix A causes B, fixing B risks
  reintroducing A) — this run hit that with `ci_gates`'s quote-stripping regex, structurally
  identical to the pre-existing `spdx_match.py` precedent — the correct move, established twice now,
  is: stop patching the same heuristic-approach family, keep whichever fix has the less-bad failure
  mode, and honestly document the residual limitation (xfail test + METHODOLOGY.md) rather than
  attempt an open-ended Nth patch.
- Only merge to `dev`. Never touch `main`, never force-push, never push to `origin`.
- Attribution: commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Immediate next steps for whoever/whatever picks this up

1. Independently re-verify the last 2 of the original 9: `deps_audit` extension, the `trivy` fix.
2. Optional, lower priority: `testquality.py`'s package restructuring (580+ lines) and wiring its 3
   static signals into `deep_reports.py`/`per_repo_digest.py` (currently dead CSV-only output); and
   making its 3 fuzz-usage regexes comment-aware (see "In-flight" above).
3. Re-scan `docs/checklist-by-repo-type/single-repo.md`'s remaining sections. "Codebase Structure &
   Internal Modularity" is now **fully covered** (confirmed this run by reading `codebase_modularity/
   __init__.py`'s own docstring: circular deps + fan-in/fan-out via `depgraph.py`, feature-flag debt
   via `flag_debt/`, size/god-class/layering via `codebase_modularity/` itself — nothing left in that
   section). "Maintainability & Technical Debt"'s "Tech debt backlog size & age" row is now covered
   by this run's new `debt_markers` collector. Remaining genuinely-uncovered single-repo rows are
   mostly either live-execution-requiring (sign-off-gate territory, same situation as `affected.py`)
   or thin single-metric items (e.g. "Onboarding time-to-first-commit") not yet worth a dedicated
   collector — no large, well-scoped, keyless single-repo gap was found this run beyond what got
   built. `polyrepo.md`/`monorepo.md` were not re-audited this run (time went to the verification
   backlog instead) — worth a fresh look next run before assuming they're thin too.
4. Do not fan out more than 1-2 new builders per run unless verification capacity is confirmed
   available. This run's own experience: a single collector's fix cycle (`ci_gates`) consumed 4
   builder+verifier round-trips on its own — budget accordingly, and don't assume every FAIL is a
   quick one-round fix.
5. Rewrite this file with real, git-verified state at the end of every run.
