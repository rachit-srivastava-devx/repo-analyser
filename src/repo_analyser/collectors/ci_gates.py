"""CI gate reality check: does CI actually run tests before merge/deploy, or
is it deploy-only?

This exists because an earlier reference analysis got this wrong for 27
repos in one portfolio (it looked for per-repo CI config in the wrong place
and concluded "no CI" for repos that had it centrally). The fix there was
"go read the actual CI config, don't infer it." This module does that directly:
it parses every GitHub Actions workflow file and checks whether any step
plausibly executes the test suite, rather than assuming a workflow's
existence means tests run.

Two more gates live here for the same reason (they're small, repo-config-file
checks in the same "don't infer it, go look" spirit -- not big enough to earn
their own external-tool-per-dimension module, see AGENTS.md §4):

- **Pre-commit hook presence**: `.pre-commit-config.yaml`, a `.husky/`
  directory, or a `"pre-commit"`/`"lint-staged"` key in `package.json`.
  Independent of whether `.github/workflows` exists at all -- a repo can gate
  locally via hooks with no CI workflow, or vice versa.
- **Lockfile discipline**: whether a lockfile is committed, AND (a separate
  question, kept as separate columns per the same duplication.py/
  exact_duplicates.py principle of not averaging two different measurements
  into one) whether any CI step actually *enforces* it (`npm ci`, not
  `npm install`, which silently rewrites the lockfile instead of failing on
  drift; `poetry check`; `cargo build|test --locked`; `go mod verify`) --
  attributed **per package manager** (`lockfile_managers_found` /
  `lockfile_managers_verified_in_ci`, both semicolon-joined), not one
  repo-wide boolean, so a monorepo with an enforced `package-lock.json`
  next to an unenforced `poetry.lock` reports both, distinguishably,
  instead of one enforced command anywhere making the whole repo look
  compliant. `lockfile_verified_in_ci` is kept alongside these (an
  already-shipped CSV column -- additive-only changes here, see AGENTS.md
  §8/§10) as a derived "was *any* manager verified" aggregate boolean, not
  a replacement for the per-manager breakdown: don't read a repo-wide
  `True` there as "every manager is compliant."
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from ..core.lang import EXCLUDE_DIR_PARTS
from ..core.util import write_csv

# A step "runs tests" if its `run:` shell text invokes a known test command.
# Deliberately conservative (word-boundary matches) to avoid false positives
# on things like "test -f file.txt" in a bash conditional.
TEST_COMMAND_PATTERNS = [
    r"\bnpm\s+(run\s+)?test\b", r"\byarn\s+test\b", r"\bpnpm\s+(run\s+)?test\b",
    r"\bvitest\b", r"\bjest\b", r"\bmocha\b", r"\bplaywright\s+test\b",
    r"\bcypress\s+run\b", r"\bnpm\s+run\s+test:", r"\bstryker\b",
    # Python and Go -- this list previously covered JS/TS only, so any
    # Python/Go repo whose CI runs `pytest`/`go test` was misreported as
    # "no workflow runs tests" (deploy-only) even when it genuinely gates on
    # a passing suite. Caught via this tool's own ci.yml (`pytest --cov=...`)
    # being misclassified in its own per-repo digest (docs/adr/0003).
    r"\bpytest\b", r"\bunittest\b", r"\bgo\s+test\b",
]
TEST_RE = re.compile("|".join(TEST_COMMAND_PATTERNS), re.IGNORECASE)

DEPLOY_HINTS = re.compile(r"\b(docker build|ecr|ecs|kubectl|helm|deploy|push image)\b", re.IGNORECASE)

# Pre-commit hook presence: any one of these is sufficient evidence -- a repo
# only needs one working mechanism, not all three.
PRECOMMIT_CONFIG_FILENAME = ".pre-commit-config.yaml"
HUSKY_DIRNAME = ".husky"
PACKAGE_JSON_PRECOMMIT_KEYS = ("pre-commit", "lint-staged")

# Lockfile discipline, part 1: presence. Order doesn't matter -- every
# matching name found is reported (see _lockfiles_found), not just the first,
# because "two different lockfiles committed at once" (e.g. both
# package-lock.json and yarn.lock) is itself a real, if unusual, finding
# worth surfacing rather than silently collapsing to one. Scanned repo-wide
# (not just the repo root) so a monorepo with lockfiles in per-package
# subdirectories (e.g. packages/api/package-lock.json) isn't reported as
# having none just because the root has none -- reuses core.lang's
# EXCLUDE_DIR_PARTS so this walk skips node_modules/vendor/etc the same way
# detect_repo_language already does, rather than inventing a second
# exclusion list that could quietly drift from it.
#
# Each lockfile name also maps to the package manager that owns it -- used
# to attribute lockfile-verification-in-CI per manager (see
# LOCKFILE_VERIFY_PATTERNS_BY_MANAGER below) instead of collapsing every
# manager in a monorepo into one global "verified" bit. LOCKFILE_NAMES is
# derived from this mapping's keys, not hand-duplicated, so the two can't
# drift apart.
LOCKFILE_MANAGER_BY_FILENAME: dict[str, str] = {
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "Cargo.lock": "cargo",
    "go.sum": "go",
}
LOCKFILE_NAMES = tuple(LOCKFILE_MANAGER_BY_FILENAME)

# Lockfile discipline, part 2: does any CI step actually *enforce* the
# lockfile rather than merely having one committed? `npm install` is
# deliberately excluded -- it silently rewrites package-lock.json on drift
# instead of failing the build, so it does not belong here even though it
# touches the same file. Scoped to `run:` text only (unlike TEST_RE, which
# also checks `uses:`): none of these are ever invoked as a marketplace
# action, only as a literal shell command.
#
# Keyed by manager (not a flat list) so a monorepo with, say, an unenforced
# poetry.lock next to a properly-enforced package-lock.json can be
# attributed correctly instead of one enforced command anywhere in the repo
# making the whole repo look compliant (AGENTS.md §4: don't average two
# different measurements into one number). Only npm/poetry/cargo/go have a
# known enforcement command wired up here -- pnpm/yarn/pipenv lockfiles are
# still detected as *present* (LOCKFILE_MANAGER_BY_FILENAME above) but never
# appear as "verified," a disclosed gap, not a silent one (see
# docs/METHODOLOGY.md).
LOCKFILE_VERIFY_PATTERNS_BY_MANAGER: dict[str, re.Pattern[str]] = {
    "npm": re.compile(r"\bnpm\s+ci\b", re.IGNORECASE),
    "poetry": re.compile(r"\bpoetry\s+check\b", re.IGNORECASE),
    "cargo": re.compile(r"\bcargo\s+(?:build|test)\b[^\n]*?--locked\b", re.IGNORECASE),
    "go": re.compile(r"\bgo\s+mod\s+verify\b", re.IGNORECASE),
}
# Combined form, kept for the repo-wide "was anything verified at all"
# question -- derived from the per-manager patterns above (single source of
# truth) rather than a hand-duplicated pattern list.
LOCKFILE_VERIFY_RE = re.compile(
    "|".join(p.pattern for p in LOCKFILE_VERIFY_PATTERNS_BY_MANAGER.values()), re.IGNORECASE,
)

# A `run:` block is a literal shell script, and its text can legitimately
# contain a bash comment line that merely *mentions* a verification command
# ("# remember: prod uses npm ci") -- or a quoted string doing the same
# thing in a real, executed command ('echo "we should switch to npm ci"')
# -- without invoking it either way. A bare substring search against the
# raw text can't distinguish "npm ci" the invocation from "npm ci" the words
# inside an echoed message, so both whole-line comments and quoted-string
# spans are stripped before matching. This is still a regex over text, not a
# shell parser: a real invocation deliberately wrapped in its own quotes
# (e.g. `bash -c "npm ci"`) is not detected by this fix -- a known,
# disclosed limitation (see docs/METHODOLOGY.md), not a silent one.
#
# The negated character classes below deliberately exclude "\n" as well as
# the quote char and backslash: `run:` is a multi-line block-scalar script,
# and an *unbalanced* quote (a plain English contraction like "Don't" or
# "it's" inside an echoed message, with no closing quote on the same
# logical string) must not be allowed to greedily span past its own line
# looking for the next matching quote anywhere later in the script --
# doing so would swallow real, unrelated commands (like a genuine `npm ci`
# step) sitting between the contraction and the next quoted string. A
# quoted string is a single-line construct in every shell dialect this
# module cares about, so refusing to match across a newline is correct, not
# a narrowing of the original fix.
_COMMENT_LINE_RE = re.compile(r"^\s*#")
_QUOTED_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')


def _strip_comment_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not _COMMENT_LINE_RE.match(line))


def _strip_quoted_strings(text: str) -> str:
    return _QUOTED_STRING_RE.sub(" ", text)


def _cleaned_run_text(run_text: str) -> str:
    """Text a lockfile-verification pattern should actually be matched
    against: whole-line comments and quoted-string spans removed, so neither
    a comment mentioning a command nor an echoed string containing its words
    can be mistaken for the command actually running (see module-level note
    above `_COMMENT_LINE_RE`)."""
    return _strip_quoted_strings(_strip_comment_lines(run_text))


def _iter_run_texts(doc: dict) -> list[str]:
    jobs = (doc or {}).get("jobs") or {}
    texts = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            texts.append(step.get("run", "") or "")
    return texts


@dataclass
class CIGateResult:
    repo: str
    has_ci_config: bool
    workflow_count: int
    workflow_files: str
    any_workflow_runs_tests: bool
    all_workflows_deploy_only: bool
    triggers: str
    has_precommit_hook: bool
    precommit_signals: str
    lockfile_present: bool
    lockfiles_found: str
    lockfile_managers_found: str
    lockfile_managers_verified_in_ci: str
    # Derived "any manager verified" aggregate -- True iff
    # lockfile_managers_verified_in_ci is non-empty (at least one manager
    # verified), computed from that exact same verified_managers set, not a
    # separate re-implementation. This is repo-wide and coarser than the
    # per-manager breakdown above: a monorepo can have this True while only
    # one of several lockfile managers is actually enforced, so treat
    # `lockfile_managers_verified_in_ci` as the authoritative per-manager
    # answer and this field only as a quick "was anything at all enforced"
    # bit -- reading a repo-wide True here as "every manager is compliant"
    # is exactly the conflation bug this module's fix exists to prevent.
    lockfile_verified_in_ci: bool


def _workflow_runs_tests(doc: dict) -> bool:
    jobs = (doc or {}).get("jobs") or {}
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            run_text = step.get("run", "") or ""
            uses_text = step.get("uses", "") or ""
            if TEST_RE.search(run_text) or TEST_RE.search(uses_text):
                return True
    return False


def _workflow_is_deploy_only(doc: dict) -> bool:
    jobs = (doc or {}).get("jobs") or {}
    saw_deploy = False
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            text = f"{step.get('run', '')} {step.get('uses', '')} {step.get('name', '')}"
            if DEPLOY_HINTS.search(text):
                saw_deploy = True
    return saw_deploy


def _workflow_verifies_lockfile(doc: dict) -> bool:
    return any(LOCKFILE_VERIFY_RE.search(_cleaned_run_text(t)) for t in _iter_run_texts(doc))


def _workflow_verified_lockfile_managers(doc: dict) -> set[str]:
    """Which package managers (see LOCKFILE_VERIFY_PATTERNS_BY_MANAGER) have
    a real, invoked enforcement command somewhere in this workflow doc --
    the per-manager counterpart to _workflow_verifies_lockfile, so a
    monorepo with several lockfile types can have each attributed
    correctly instead of collapsed into one repo-wide bit."""
    managers: set[str] = set()
    for run_text in _iter_run_texts(doc):
        cleaned = _cleaned_run_text(run_text)
        for manager, pattern in LOCKFILE_VERIFY_PATTERNS_BY_MANAGER.items():
            if pattern.search(cleaned):
                managers.add(manager)
    return managers


def _package_json_precommit_signal(repo: Path) -> str | None:
    """Which of PACKAGE_JSON_PRECOMMIT_KEYS is present as a top-level key in
    package.json, e.g. "package.json:lint-staged" -- or None if the file is
    absent, unreadable, not a JSON object, or has neither key. A malformed
    package.json is treated as "no signal from this source" rather than
    raised: it's one of three independent precommit signals (the other two
    are plain file/dir existence checks unaffected by it), unlike a
    malformed workflow yaml, which is the *sole* source for that workflow's
    entire test-running signal -- see the ValueError path in analyze_repo."""
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    for key in PACKAGE_JSON_PRECOMMIT_KEYS:
        if key in data:
            return f"package.json:{key}"
    return None


def _precommit_signals(repo: Path) -> list[str]:
    signals = []
    if (repo / PRECOMMIT_CONFIG_FILENAME).is_file():
        signals.append(PRECOMMIT_CONFIG_FILENAME)
    if (repo / HUSKY_DIRNAME).is_dir():
        signals.append(HUSKY_DIRNAME)
    pkg_signal = _package_json_precommit_signal(repo)
    if pkg_signal:
        signals.append(pkg_signal)
    return sorted(signals)


def _lockfiles_found(repo: Path) -> list[str]:
    """Repo-relative paths of every committed lockfile, anywhere under
    `repo` -- not just at the root -- so a monorepo with lockfiles in
    per-package subdirectories reports all of them, not just a root one
    (or none, if the root has none but subdirectories do)."""
    found = []
    for p in repo.rglob("*"):
        if p.name in LOCKFILE_NAMES and p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            found.append(p.relative_to(repo).as_posix())
    return sorted(found)


def _lockfile_managers_found(lockfiles_found: list[str]) -> list[str]:
    """Package managers implied by an already-computed _lockfiles_found()
    list -- e.g. ["packages/api/package-lock.json"] -> ["npm"]. Sorted,
    deduplicated: a monorepo with two package-lock.json files in different
    subdirectories is still just one manager ("npm"), not two."""
    return sorted({LOCKFILE_MANAGER_BY_FILENAME[Path(p).name] for p in lockfiles_found})


def analyze_repo(repo: Path) -> CIGateResult:
    # Independent of whether .github/workflows exists at all -- a repo can
    # have local pre-commit hooks and a committed lockfile with zero GitHub
    # Actions workflows, and that combination must not be silently reported
    # as "no signal" just because the CI-workflow branch below returns early.
    precommit_signals = _precommit_signals(repo)
    lockfiles_found = _lockfiles_found(repo)
    lockfile_managers_found = _lockfile_managers_found(lockfiles_found)

    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return CIGateResult(
            repo=repo.name, has_ci_config=False, workflow_count=0, workflow_files="",
            any_workflow_runs_tests=False, all_workflows_deploy_only=False, triggers="",
            has_precommit_hook=bool(precommit_signals),
            precommit_signals=";".join(precommit_signals),
            lockfile_present=bool(lockfiles_found),
            lockfiles_found=";".join(lockfiles_found),
            lockfile_managers_found=";".join(lockfile_managers_found),
            # No workflows exist, so no CI step could possibly have verified
            # any manager's lockfile -- this is a known fact, not a guess,
            # same as any_workflow_runs_tests=False on this same early-return
            # path.
            lockfile_managers_verified_in_ci="",
            lockfile_verified_in_ci=False,
        )

    files = sorted([p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")])
    any_tests = False
    any_deploy = False
    verified_managers: set[str] = set()
    triggers: set[str] = set()
    parse_errors = []
    for f in files:
        try:
            doc = yaml.safe_load(f.read_text())
        except yaml.YAMLError as e:
            parse_errors.append(f"{f.name}: {e}")
            continue
        if not isinstance(doc, dict):
            continue
        if _workflow_runs_tests(doc):
            any_tests = True
        if _workflow_is_deploy_only(doc):
            any_deploy = True
        verified_managers |= _workflow_verified_lockfile_managers(doc)
        on = doc.get("on") or doc.get(True)  # YAML parses bare `on:` key as True in some loaders
        if isinstance(on, dict):
            triggers.update(on.keys())
        elif isinstance(on, (list, str)):
            triggers.update(on if isinstance(on, list) else [on])

    if parse_errors:
        raise ValueError(f"{repo.name}: unparseable workflow(s): {parse_errors}")

    return CIGateResult(
        repo=repo.name,
        has_ci_config=True,
        workflow_count=len(files),
        workflow_files=";".join(f.name for f in files),
        any_workflow_runs_tests=any_tests,
        all_workflows_deploy_only=(any_deploy and not any_tests),
        triggers=";".join(sorted(triggers)),
        has_precommit_hook=bool(precommit_signals),
        precommit_signals=";".join(precommit_signals),
        lockfile_present=bool(lockfiles_found),
        lockfiles_found=";".join(lockfiles_found),
        lockfile_managers_found=";".join(lockfile_managers_found),
        lockfile_managers_verified_in_ci=";".join(sorted(verified_managers)),
        lockfile_verified_in_ci=bool(verified_managers),
    )


def run_ci_gates(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "ci_gates.csv"
    write_csv(out_path, rows, fieldnames=CIGateResult)
    return out_path
