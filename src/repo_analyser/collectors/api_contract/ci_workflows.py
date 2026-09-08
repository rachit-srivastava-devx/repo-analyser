"""Shared GitHub Actions workflow loading + step-text extraction, reused by
ci_signals.py and contract_testing.py. Reads the actual CI config rather
than inferring it -- ci_gates.py's own docstring documents getting this
wrong once by inferring instead of reading; this module follows its
corrected approach."""
from __future__ import annotations

from pathlib import Path

import yaml


def load_workflow_docs(repo: Path) -> tuple[list[dict], list[str]]:
    """Returns (parsed_docs, parse_errors). A malformed workflow file must
    not crash the whole collector run -- its error is reported, and the
    other workflows (and every other signal this collector computes) still
    run normally."""
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return [], []
    docs: list[dict] = []
    errors: list[str] = []
    for f in sorted(p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as e:
            errors.append(f"{f}: {e}")
            continue
        if isinstance(doc, dict):
            docs.append(doc)
    return docs, errors


def strip_comment_lines(text: str) -> str:
    """Drops any line whose stripped form starts with '#' before command
    matching -- avoids the false positive of a bash comment merely
    *mentioning* a tool inside a `run:` block's shell text (e.g.
    `# TODO: wire up oasdiff breaking` must not count as running it)."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def step_texts(doc: dict) -> list[str]:
    """Same shape as ci_gates.py's own helper, hardened one step further: a
    workflow YAML can be syntactically valid but structurally malformed for
    a real workflow (e.g. `jobs: "not a mapping"`); a non-dict `jobs` or
    non-list `steps` yields no evidence rather than raising."""
    texts: list[str] = []
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return texts
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict):
                run_text = strip_comment_lines(str(step.get("run", "")))
                texts.append(f"{run_text} {step.get('uses', '')}")
    return texts
