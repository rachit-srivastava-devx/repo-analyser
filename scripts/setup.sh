#!/bin/bash
# One-command environment setup: venv + editable install, code-maat.jar,
# and every external scanner repo-analyser shells out to. Idempotent --
# safe to re-run after a partial failure, or just to pick up a newly-added
# requirement.
#
# Deliberately NOT `set -e`: this script checks ~10 independent things and
# reports one summary at the end (see `note()`/`FAILED`/`SOFT_FAILED` below)
# rather than dying opaquely on the first missing tool -- a fresh machine
# with nothing installed needs to see every gap in one run, not one per
# re-run. `-u`/pipefail stay on to catch real script bugs.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR" || exit 1

# Hard requirements: the package/test suite cannot run at all without these,
# so a failure here fails the script (and, in CI, the job).
FAILED=()
# External scanners: real modules degrade to an explicit `skipped_reason`
# when these are missing (see README's module table / AGENTS.md's
# "silent empty result" failure mode) -- so absence here is reported, never
# fatal. This mirrors CI's own ci.yml, which deliberately skips installing
# most of these on its Linux runner and relies on the same graceful-skip path.
SOFT_FAILED=()

ok()   { echo "  OK    $1"; }
skip() { echo "  SKIP  $1 (already present)"; }
note() { echo "  --    $1"; }
hard_fail() { echo "  FAIL  $1: $2"; FAILED+=("$1"); }
soft_fail() { echo "  MISS  $1: $2"; SOFT_FAILED+=("$1"); }

# Runs "$@", and on nonzero exit prints the last 20 lines of its combined
# output (not swallowed -- AGENTS.md's stderr-truncate-don't-discard rule).
run_logged() {
  local out
  if out="$("$@" 2>&1)"; then
    return 0
  else
    echo "$out" | tail -20 | sed 's/^/         /'
    return 1
  fi
}

echo "--- Python environment ---"
if [ -d .venv ] && [ ! -x .venv/bin/pip ]; then
  hard_fail "venv" ".venv exists but has no pip -- remove it and re-run, or fix it by hand"
elif [ ! -d .venv ]; then
  if run_logged python3 -m venv .venv; then
    ok "created .venv"
  else
    hard_fail "venv" "python3 -m venv .venv failed"
  fi
fi
if [ -x .venv/bin/pip ]; then
  if run_logged .venv/bin/pip install -e ".[dev]"; then
    ok "repo-analyser installed (editable, dev extras) in .venv"
  else
    hard_fail "pip install" "pip install -e '.[dev]' failed -- see output above"
  fi
fi

echo "--- code-maat.jar (churn) ---"
JAR="$DIR/tools/code-maat.jar"
if [ -f "$JAR" ]; then
  skip "code-maat.jar"
else
  mkdir -p "$DIR/tools"
  URL="https://github.com/adamtornhill/code-maat/releases/download/v1.0.4/code-maat-1.0.4-standalone.jar"
  if run_logged curl -sL -o "$JAR" "$URL" && file "$JAR" | grep -q "Java archive"; then
    ok "code-maat.jar fetched"
  else
    rm -f "$JAR"
    hard_fail "code-maat.jar" "download/verify failed from $URL"
  fi
fi

echo "--- External scanners (optional -- missing ones degrade gracefully) ---"
HAVE_BREW=0; command -v brew >/dev/null 2>&1 && HAVE_BREW=1
HAVE_NPM=0;  command -v npm  >/dev/null 2>&1 && HAVE_NPM=1

# name on PATH, brew formula (same names README already documents)
brew_install() {
  if command -v "$1" >/dev/null 2>&1; then skip "$1"; return; fi
  if [ "$HAVE_BREW" = 1 ]; then
    if run_logged brew install "$2"; then ok "$1 (brew install $2)"; else soft_fail "$1" "brew install $2 failed -- see output above"; fi
  else
    soft_fail "$1" "not found, and Homebrew isn't installed -- see https://brew.sh, then: brew install $2"
  fi
}
brew_install gitleaks gitleaks
brew_install semgrep semgrep
brew_install osv-scanner osv-scanner
brew_install trivy trivy

if command -v jscpd >/dev/null 2>&1; then
  skip "jscpd"
elif [ "$HAVE_NPM" = 1 ]; then
  if run_logged npm install -g jscpd; then ok "jscpd (npm install -g)"; else soft_fail "jscpd" "npm install -g jscpd failed -- see output above"; fi
else
  soft_fail "jscpd" "not found, and npm isn't installed -- install Node.js, then: npm install -g jscpd"
fi

echo "--- Language runtimes + optional lint tools (checked, never auto-installed) ---"
check_only() {
  if command -v "$1" >/dev/null 2>&1; then ok "$1"; else note "$1 not found -- $2"; fi
}
check_only java       "required for churn -- brew install openjdk"
check_only node       "required for JS/TS depgraph/testquality/mutation -- brew install node"
check_only go         "required for Go targets -- brew install go"
check_only staticcheck "optional, Go lint_quality -- go install honnef.co/go/tools/cmd/staticcheck@latest"

echo
if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "Setup failed: ${FAILED[*]}"
  echo "Fix the FAIL lines above and re-run -- already-OK steps are skipped."
  exit 1
fi
if [ "${#SOFT_FAILED[@]}" -gt 0 ]; then
  echo "Core setup OK. ${#SOFT_FAILED[@]} optional scanner(s) not installed: ${SOFT_FAILED[*]}"
  echo "The matching module(s) will report an explicit skipped_reason rather than run -- see the MISS lines above to fix."
fi
echo "Try: repo-analyser analyze /path/to/repo"
