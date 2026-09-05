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

Not yet built. Confirmed absent via full-codebase grep (2026-09-05): the only near-miss hits are
`ontology.py`'s commit-message classifier (labels a commit "perf" if its message mentions
performance/latency — never measures anything) and `escape.py`'s "fix latency" (calendar days a bug
lived before a fix — a defect-lifecycle metric, not application runtime latency). Nothing in this
codebase runs a benchmark, a load test, or reads a performance budget for any *target* repo.

Real tools to wrap, following this codebase's existing "one collector = one external tool" rule
(ADR-0002) and its "presence + CI-wiring, not full live execution" precedent (`e2e_quality.py`
already does exactly this for E2E suites rather than actually driving a browser):

- **Budget presence + CI-wiring** (the safe default, mirrors `e2e_quality.py`): detect a Lighthouse
  CI config (`.lighthouserc.js`/`.json` with `assertions`), a `k6`/`artillery`/`autocannon` script,
  or a bundlesize/`size-limit` config — and whether it's wired into CI (same
  `.github/workflows` parsing `ci_gates.py` already does). No live server required.
- **Real benchmark execution where one already exists** (matches `testquality.py`'s "actually run
  it" philosophy, same timeout discipline via `core.util.run()`): Go's `go test -bench=. -benchmem`,
  Python's `pytest-benchmark` (only if the target already depends on it — never installed by this
  tool into a target repo), JS/TS benchmark frameworks (`vitest bench`, `tinybench`). Report real
  numbers (ns/op, allocations) with a `repo` column like every other collector's CSV.
- Absence of any of the above is an explicit `skipped_reason` ("no benchmark suite or budget config
  found"), never a silently empty result (ADR-0001) — this is exactly the gap
  `per_repo_digest.py`'s `_section_performance` already renders explicitly (ADR-0003) pending this
  collector.

Acceptance bar: run against a real target that has an actual benchmark suite (not a fixture) and
show the real numbers landing in `performance_summary.csv`, then confirm `per_repo_digest.py`'s
performance section picks them up without any change to that file (it already reads
`performance_summary.csv` by convention — see `_AllData.performance`).

## Recurring / CI-integrated runs

Not yet built. The goal this serves: catching regressions (a newly-ungated repo, a newly-committed
secret, a mutation score that dropped) as they happen, not only when someone remembers to run this
tool by hand — and doing it both for a single repo's own CI and across a whole portfolio like
`posx` or `chronicle_button`'s `button` estate.

Planned shape: a reusable GitHub Actions workflow this repo publishes (`workflow_call` trigger) that
a target repo or portfolio-meta-repo's own CI can invoke two ways — on a `schedule:` cron, and via
`workflow_run` after that repo's own E2E workflow completes. Both feed the same `--out` dir run over
run, so the existing `trends.py` (regressions/improvements vs. the last run in the same `--out`
dir) already has the mechanism to surface "this got worse since last run" — recurring invocation is
what actually exercises it. `trends.py` today diffs portfolio-wide numbers; whether it also needs a
per-repo-digest-aware diff (this specific repo's mutation score dropped, not just the portfolio
mean) is a real open question for whoever picks this up, not assumed solved by this note.

Acceptance bar: the reusable workflow actually runs (a real invocation from a real caller
workflow, not a dry-run/lint of the YAML) and produces a second data point in `trends.py`'s output
for a target that already has one prior run.
