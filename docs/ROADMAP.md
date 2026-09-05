# Roadmap

Forward-looking work, as distinct from `docs/METHODOLOGY.md` (a log of bugs already found and
fixed) and `CHANGELOG.md` (a log of what shipped). Not a commitment or a schedule — a backlog.

## Verify repo-analyser's own process health (memory, CPU, threads)

Not yet done: repo-analyser runs many external subprocesses across a portfolio (one lizard/jscpd/
semgrep/gitleaks/osv-scanner/mutmut/Stryker invocation per repo, sometimes dozens of repos per
run), and nothing currently confirms its own Python process doesn't accumulate memory across that
— open file handles, temp directories, subprocess objects, growing in-memory lists — over a long
portfolio run. Given this session's own crash history (`docs/METHODOLOGY.md` #23), resource
behavior here isn't a hypothetical concern.

Concrete, real tools to add for this, not a generic "add profiling" placeholder:

- **Memory-leak detection**: `tracemalloc` (stdlib, zero new dependency — snapshot allocations
  before and after a full portfolio run, diff the top allocators) as the first, cheapest check.
  `memray` (Bloomberg, MIT) if a deeper look is needed — can wrap a full CLI invocation
  (`memray run -- python3 -m repo_analyser analyze ...`) and produce a flamegraph without any code
  changes to this tool.
- **CPU profiling**: `py-spy` — a sampling profiler that attaches to a running process by PID with
  no code changes, well suited to a tool that spends most of its wall-clock time waiting on
  subprocesses rather than doing its own computation (it will show that split clearly: time in
  this tool's own Python vs. time inside `lizard`/`jscpd`/etc.). `scalene` as an alternative with
  built-in memory+CPU line-level attribution in one run.
- **Thread optimization checks**: verified via `grep` (2026-09-05) that `src/repo_analyser/`
  currently has zero `threading`/`multiprocessing`/`ThreadPoolExecutor` usage of its own — every
  collector runs its subprocess calls sequentially. There is nothing to check here yet. Revisit
  only if/when this codebase actually introduces concurrency of its own (e.g., running multiple
  repos' collectors in parallel) — adding a thread-safety checker ahead of having any threads would
  be checking nothing.

Acceptance bar for this item, once picked up: run one of the above against a real, multi-repo
portfolio-scale invocation (not a synthetic fixture) and report real numbers — a passing check on
a toy input would be the same "denominator dishonesty" this repo's own methodology explicitly
argues against.

## Runtime performance / latency budget collector (`performance.py`)

**Detection built** (ADR-0003 slice): `performance.py` detects a declared budget (Lighthouse CI /
bundlesize / size-limit / artillery config or dependency) and whether it's wired into CI, mirroring
`e2e_quality.py`'s presence-only shape (`docs/ARCHITECTURE.md`'s "one collector = one external tool"
rule, ADR-0002) — writes `performance.csv`/`performance_summary.json`, read by
`per_repo_digest.py`'s `_AllData.performance`. Before this, confirmed absent via full-codebase grep
(2026-09-05): the only near-miss hits were `ontology.py`'s commit-message classifier (labels a
commit "perf" if its message mentions performance/latency — never measures anything) and
`escape.py`'s "fix latency" (calendar days a bug lived before a fix — a defect-lifecycle metric, not
application runtime latency).

**Still open: real benchmark execution.** `performance.py` only answers "is a budget declared and
enforced in CI" — it never runs one. Matching `testquality.py`'s "actually run it" philosophy (same
timeout discipline via `core.util.run()`): Go's `go test -bench=. -benchmem`, Python's
`pytest-benchmark` (only if the target already depends on it — never installed by this tool into a
target repo), JS/TS benchmark frameworks (`vitest bench`, `tinybench`). Report real numbers (ns/op,
allocations) as new columns on the same `performance.csv`, keeping the `repo` column every other
collector's CSV already has.

Acceptance bar for the execution half: run against a real target that has an actual benchmark suite
(not a fixture) and show the real numbers landing in `performance.csv`, then confirm
`per_repo_digest.py`'s performance section picks them up with only an additive change to
`_section_performance` (the budget-detection half of that section is already live and shouldn't
need to change).

## Recurring / CI-integrated runs

**Built**: `.github/workflows/analyze-reusable.yml`, a `workflow_call` reusable workflow a target
repo (or portfolio-meta-repo) invokes on a `schedule:` cron and/or via `workflow_run` after its own
E2E workflow completes — see README's "Recurring analysis" section for the exact caller snippets.
Caches `analyses/` between runs (`actions/cache`, private to the calling repo — never a public
artifact or a commit, since that output carries real secret-scan/CVE data) so `trends.py` has a
prior baseline from the second run onward.

**Verified**: YAML validity, correct `workflow_call` input/output structure, and the embedded shell
is `shellcheck`-clean (including a fix for interpolating `${{ inputs.* }}` directly into `run:`
script text — GitHub's own documented script-injection anti-pattern, caught by rerunning shellcheck
after writing it; now passed via `env:` instead, matching this codebase's existing "no unsanitized
input into a shell string" rule).

**Not verified, stated plainly**: never executed on a live GitHub Actions runner from this
environment (no sandboxed runner available here) — untested against a real caller workflow. Do
that before relying on it in production.

**Still open**: `trends.py` today diffs portfolio-wide numbers only. Whether it also needs a
per-repo-digest-aware diff (this specific repo's mutation score dropped, not just the portfolio
mean) is a real open question for whoever picks this up next, not assumed solved by this workflow
existing.
