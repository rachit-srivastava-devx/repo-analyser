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
