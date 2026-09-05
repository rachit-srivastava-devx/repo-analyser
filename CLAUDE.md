# CLAUDE.md — entrypoint for Claude Code

> The manual is [`AGENTS.md`](AGENTS.md). Read it before touching anything — it is the operating
> contract, not background reading.

## Session ritual

1. **Bearings** — `AGENTS.md` §0–2, then `docs/ARCHITECTURE.md` for which subpackage owns what
   you're about to touch.
2. **One thing** — one collector, one bug, one doc. Don't one-shot a sweep across the package.
3. **Reuse check** — a new measured dimension is a new `collectors/*.py` module following the
   existing shape (`AGENTS.md` §11); check nothing existing half-covers it first.
4. **Build** behind the contract in `AGENTS.md` §3 (edge-case ladder) and §4 (design bar).
5. **Verify** — `AGENTS.md` §5, all three layers. Paste real output, red included.
6. **Report** — `AGENTS.md` §7's block. No victory-lap prose.

## Before claiming anything is done, verified, or tested

Load the `l8-engineer` behavioral standard if it's available as a skill in this session, or apply
`AGENTS.md` §5–6 directly: a passing test is the floor, not the bar; an HTTP-200-shaped proxy is
not the property; re-run anything that involves subprocess timing or a real external tool before
trusting a single green result.

## What this repo is, in one paragraph

A CLI (`repo-analyser` / `python3 -m repo_analyser`) that runs real, already-existing open-source
tools (PyDriller, code-maat, lizard, jscpd, dependency-cruiser, gitleaks, semgrep, osv-scanner,
Stryker/mutmut, ESLint/ruff/staticcheck, networkx, matplotlib, WeasyPrint) against a git repo or a
portfolio of repos, and turns their raw output into CSV/JSON plus a doctrine-styled PDF report —
so that every number in the report traces back to a rerunnable command. See `README.md` for the
full module table and `docs/METHODOLOGY.md` for the exact formula and known bugs behind each one.

**Before pointing this at any repo**: read README's "Security model" section
(`docs/ARCHITECTURE.md` has the full breakdown). This tool executes arbitrary target-repo code by
design (`testquality`/`mutation` actually run each repo's test suite) — only run it against repos
you already trust.
