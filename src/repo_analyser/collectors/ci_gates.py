"""CI gate reality check: does CI actually run tests before merge/deploy, or
is it deploy-only?

This exists because an earlier reference analysis got this wrong for 27
repos in one portfolio (it looked for per-repo CI config in the wrong place
and concluded "no CI" for repos that had it centrally). The fix there was
"go read the actual CI config, don't infer it." This module does that directly:
it parses every GitHub Actions workflow file and checks whether any step
plausibly executes the test suite, rather than assuming a workflow's
existence means tests run.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from ..core.util import write_csv

# A step "runs tests" if its `run:` shell text invokes a known test command.
# Deliberately conservative (word-boundary matches) to avoid false positives
# on things like "test -f file.txt" in a bash conditional.
TEST_COMMAND_PATTERNS = [
    r"\bnpm\s+(run\s+)?test\b", r"\byarn\s+test\b", r"\bpnpm\s+(run\s+)?test\b",
    r"\bvitest\b", r"\bjest\b", r"\bmocha\b", r"\bplaywright\s+test\b",
    r"\bcypress\s+run\b", r"\bnpm\s+run\s+test:", r"\bstryker\b",
]
TEST_RE = re.compile("|".join(TEST_COMMAND_PATTERNS), re.IGNORECASE)

DEPLOY_HINTS = re.compile(r"\b(docker build|ecr|ecs|kubectl|helm|deploy|push image)\b", re.IGNORECASE)


@dataclass
class CIGateResult:
    repo: str
    has_ci_config: bool
    workflow_count: int
    workflow_files: str
    any_workflow_runs_tests: bool
    all_workflows_deploy_only: bool
    triggers: str


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


def analyze_repo(repo: Path) -> CIGateResult:
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return CIGateResult(repo.name, False, 0, "", False, False, "")

    files = sorted([p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")])
    any_tests = False
    any_deploy = False
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
    )


def run_ci_gates(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "ci_gates.csv"
    write_csv(out_path, rows)
    return out_path
