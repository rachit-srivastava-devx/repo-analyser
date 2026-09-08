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
  question, kept as a separate column per the same duplication.py/
  exact_duplicates.py principle of not averaging two different measurements
  into one) whether any CI step actually *enforces* it (`npm ci`, not
  `npm install`, which silently rewrites the lockfile instead of failing on
  drift; `poetry check`; `cargo build|test --locked`; `go mod verify`).
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
LOCKFILE_NAMES = (
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "poetry.lock", "Pipfile.lock", "Cargo.lock", "go.sum",
)

# Lockfile discipline, part 2: does any CI step actually *enforce* the
# lockfile rather than merely having one committed? `npm install` is
# deliberately excluded -- it silently rewrites package-lock.json on drift
# instead of failing the build, so it does not belong here even though it
# touches the same file. Scoped to `run:` text only (unlike TEST_RE, which
# also checks `uses:`): none of these are ever invoked as a marketplace
# action, only as a literal shell command.
LOCKFILE_VERIFY_PATTERNS = [
    r"\bnpm\s+ci\b",
    r"\bpoetry\s+check\b",
    r"\bcargo\s+(?:build|test)\b[^\n]*?--locked\b",
    r"\bgo\s+mod\s+verify\b",
]
LOCKFILE_VERIFY_RE = re.compile("|".join(LOCKFILE_VERIFY_PATTERNS), re.IGNORECASE)

# A `run:` block is a literal shell script, and its text can legitimately
# contain a bash comment line that merely *mentions* a verification command
# ("# remember: prod uses npm ci") without invoking it -- stripping
# whole-line comments before matching keeps LOCKFILE_VERIFY_RE from treating
# that mention as an actual step. Deliberately simple (whole-line only, no
# quote-aware inline-comment stripping) to match this module's existing
# "conservative regex over the raw text" approach rather than growing a
# real shell parser for one edge case.
_COMMENT_LINE_RE = re.compile(r"^\s*#")


def _strip_comment_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not _COMMENT_LINE_RE.match(line))


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
    jobs = (doc or {}).get("jobs") or {}
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            run_text = step.get("run", "") or ""
            if LOCKFILE_VERIFY_RE.search(_strip_comment_lines(run_text)):
                return True
    return False


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


def analyze_repo(repo: Path) -> CIGateResult:
    # Independent of whether .github/workflows exists at all -- a repo can
    # have local pre-commit hooks and a committed lockfile with zero GitHub
    # Actions workflows, and that combination must not be silently reported
    # as "no signal" just because the CI-workflow branch below returns early.
    precommit_signals = _precommit_signals(repo)
    lockfiles_found = _lockfiles_found(repo)

    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return CIGateResult(
            repo=repo.name, has_ci_config=False, workflow_count=0, workflow_files="",
            any_workflow_runs_tests=False, all_workflows_deploy_only=False, triggers="",
            has_precommit_hook=bool(precommit_signals),
            precommit_signals=";".join(precommit_signals),
            lockfile_present=bool(lockfiles_found),
            lockfiles_found=";".join(lockfiles_found),
            # No workflows exist, so no CI step could possibly have verified
            # the lockfile -- this is a known fact, not a guess, same as
            # any_workflow_runs_tests=False on this same early-return path.
            lockfile_verified_in_ci=False,
        )

    files = sorted([p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")])
    any_tests = False
    any_deploy = False
    lockfile_verified = False
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
        if _workflow_verifies_lockfile(doc):
            lockfile_verified = True
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
        lockfile_verified_in_ci=lockfile_verified,
    )


def run_ci_gates(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "ci_gates.csv"
    write_csv(out_path, rows, fieldnames=CIGateResult)
    return out_path
