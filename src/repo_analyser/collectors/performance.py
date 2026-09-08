"""Performance/latency budget detection: does this repo declare a
performance budget at all (Lighthouse CI assertions, bundlesize/size-limit,
an artillery/k6 load-test config), and is it wired into CI -- mirrors
e2e_quality.py's own "presence + CI-wiring, not full live execution"
shape deliberately (see docs/ROADMAP.md).

v1 scope, stated honestly: detection only, no benchmark execution yet.
Actually running a Go/Python/JS benchmark suite where one exists is real,
separate follow-up work (docs/ROADMAP.md) -- this module answers "is a
budget even declared," which is the gap that was completely unaddressed
before (confirmed absent via full-codebase grep, see ROADMAP.md).

Two independent detection signals, same reasoning as e2e_quality.py: a
config file can exist before (or without) the tool being a declared
package.json dependency, and vice versa.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from ..core.util import write_csv, write_json

# CI-step text pattern for each tool's own actual invocation.
PERF_CI_COMMAND_PATTERNS = {
    "lighthouse-ci": re.compile(r"\blhci\s+(autorun|assert)\b", re.IGNORECASE),
    "bundlesize": re.compile(r"\bbundlesize\b", re.IGNORECASE),
    "size-limit": re.compile(r"\bsize-limit\b", re.IGNORECASE),
    "artillery": re.compile(r"\bartillery\s+run\b", re.IGNORECASE),
}

# npm package name -> tool label.
PERF_PACKAGE_SIGNALS = {
    "@lhci/cli": "lighthouse-ci",
    "bundlesize": "bundlesize",
    "size-limit": "size-limit",
    "@size-limit/preset-app": "size-limit",
    "artillery": "artillery",
}

# A tool's own conventional config filename(s) at the repo root.
PERF_CONFIG_FILES = {
    "lighthouse-ci": ["lighthouserc.js", "lighthouserc.json", "lighthouserc.yml", ".lighthouserc.js"],
    "bundlesize": [".bundlesizerc", ".bundlesizerc.json"],
    "artillery": ["artillery.yml", "artillery.yaml"],
}
# bundlesize/size-limit can also live as a top-level package.json key rather
# than (or in addition to) a dedicated file or dependency.
PERF_PACKAGE_JSON_KEYS = {"bundlesize": "bundlesize", "size-limit": "size-limit"}


@dataclass
class PerformanceResult:
    repo: str
    has_budget_config: bool
    budget_tool: str
    detected_via: str
    wired_into_ci: bool
    skip_reason: str


def _read_package_json(repo: Path) -> dict:
    pj = repo / "package.json"
    if not pj.exists():
        return {}
    try:
        return json.loads(pj.read_text())
    except json.JSONDecodeError:
        return {}


def _detect_tools_from_package_json(pkg: dict) -> set[str]:
    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    from_deps = {PERF_PACKAGE_SIGNALS[name] for name in all_deps if name in PERF_PACKAGE_SIGNALS}
    from_keys = {tool for tool, key in PERF_PACKAGE_JSON_KEYS.items() if key in pkg}
    return from_deps | from_keys


def _detect_tools_from_config_files(repo: Path) -> set[str]:
    return {tool for tool, filenames in PERF_CONFIG_FILES.items()
            if any((repo / name).exists() for name in filenames)}


def _load_workflow_docs(repo: Path) -> list[dict]:
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return []
    docs = []
    for f in sorted(p for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml")):
        try:
            doc = yaml.safe_load(f.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def _step_texts(doc: dict) -> list[str]:
    texts = []
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if isinstance(step, dict):
                texts.append(f"{step.get('run', '')} {step.get('uses', '')}")
    return texts


def _tools_wired_into_ci(repo: Path, tools: set[str]) -> bool:
    docs = _load_workflow_docs(repo)
    all_text = " ".join(text for doc in docs for text in _step_texts(doc))
    return any(PERF_CI_COMMAND_PATTERNS[t].search(all_text) for t in tools if t in PERF_CI_COMMAND_PATTERNS)


def analyze_repo(repo: Path) -> PerformanceResult:
    pkg = _read_package_json(repo)
    tools = _detect_tools_from_package_json(pkg) | _detect_tools_from_config_files(repo)
    if not tools:
        return PerformanceResult(
            repo.name, False, "", "", False,
            skip_reason="no performance budget config found "
                        "(lighthouse-ci, bundlesize, size-limit, or artillery)",
        )
    from_pkg = _detect_tools_from_package_json(pkg)
    from_config = _detect_tools_from_config_files(repo)
    detected_via = "both" if (from_pkg and from_config) else ("package.json" if from_pkg else "config_file")
    return PerformanceResult(
        repo=repo.name, has_budget_config=True, budget_tool=";".join(sorted(tools)),
        detected_via=detected_via, wired_into_ci=_tools_wired_into_ci(repo, tools), skip_reason="",
    )


def run_performance(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "performance.csv"
    write_csv(out_path, rows, fieldnames=PerformanceResult)
    with_budget = [r for r in rows if r["has_budget_config"]]
    write_json(out_dir / "performance_summary.json", {
        "repos_total": len(rows),
        "repos_with_budget_config": len(with_budget),
        "repos_with_budget_wired_into_ci": sum(1 for r in with_budget if r["wired_into_ci"]),
    })
    return out_path
