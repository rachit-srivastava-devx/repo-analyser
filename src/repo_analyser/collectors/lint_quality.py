"""Code quality via each repo's own linter, run with its own config --
never a config this tool invents. ESLint for JS/TS (via the repo's local
`node_modules/.bin/eslint`, not `npx`: confirmed npx's eslint can't resolve
a project's plugin-dependent config, since those plugins live only in the
project's own node_modules). ruff for Python. staticcheck for Go.

This is real static analysis (unused vars, correctness bugs, style
violations the project itself has decided matter) -- a different question
from complexity.py's cyclomatic-complexity/churn hotspots.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.lang import detect_repo_language
from ..core.util import run, run_concurrent, write_csv, write_json


@dataclass
class LintResult:
    repo: str
    linter: str
    ran: bool
    error_count: int
    warning_count: int
    files_with_issues: int
    top_rules: str
    skip_reason: str = ""


def _eslint(repo: Path) -> LintResult:
    binary = repo / "node_modules" / ".bin" / "eslint"
    has_config = any((repo / c).exists() for c in ("eslint.config.js", "eslint.config.mjs",
                                                     "eslint.config.ts", ".eslintrc.js", ".eslintrc.json"))
    if not binary.exists():
        return LintResult(repo.name, "eslint", False, 0, 0, 0, "", "eslint not in node_modules/.bin")
    if not has_config:
        return LintResult(repo.name, "eslint", False, 0, 0, 0, "", "no eslint config file found")

    res = run([str(binary), ".", "--format", "json"], cwd=repo, check=False, timeout=180)
    if not res.stdout.strip():
        return LintResult(repo.name, "eslint", False, 0, 0, 0, "", f"no output: {res.stderr[:200]}")
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return LintResult(repo.name, "eslint", False, 0, 0, 0, "", "unparseable eslint output")

    errors = sum(f.get("errorCount", 0) for f in data)
    warnings = sum(f.get("warningCount", 0) for f in data)
    files_with_issues = sum(1 for f in data if f.get("errorCount", 0) + f.get("warningCount", 0) > 0)
    rule_counts: dict[str, int] = defaultdict(int)
    for f in data:
        for m in f.get("messages", []):
            if m.get("ruleId"):
                rule_counts[m["ruleId"]] += 1
    top = ";".join(f"{r}:{c}" for r, c in sorted(rule_counts.items(), key=lambda kv: -kv[1])[:5])
    return LintResult(repo.name, "eslint", True, errors, warnings, files_with_issues, top)


RUFF_SUMMARY_RE = re.compile(r"Found (\d+) error")


def _ruff(repo: Path) -> LintResult:
    import shutil
    if not shutil.which("ruff"):
        return LintResult(repo.name, "ruff", False, 0, 0, 0, "", "ruff not on PATH")
    res = run(["ruff", "check", ".", "--output-format", "json"], cwd=repo, check=False, timeout=120)
    if not res.stdout.strip():
        return LintResult(repo.name, "ruff", True, 0, 0, 0, "")
    try:
        issues = json.loads(res.stdout)
    except json.JSONDecodeError:
        return LintResult(repo.name, "ruff", False, 0, 0, 0, "", "unparseable ruff output")
    files = {i["filename"] for i in issues}
    rule_counts: dict[str, int] = defaultdict(int)
    for i in issues:
        rule_counts[i.get("code", "?")] += 1
    top = ";".join(f"{r}:{c}" for r, c in sorted(rule_counts.items(), key=lambda kv: -kv[1])[:5])
    return LintResult(repo.name, "ruff", True, len(issues), 0, len(files), top)


def _staticcheck(repo: Path) -> LintResult:
    import shutil
    if not shutil.which("staticcheck") or not (repo / "go.mod").exists():
        return LintResult(repo.name, "staticcheck", False, 0, 0, 0, "", "staticcheck or go.mod unavailable")
    res = run(["staticcheck", "-f", "json", "./..."], cwd=repo, check=False, timeout=180)
    if not res.stdout.strip():
        return LintResult(repo.name, "staticcheck", True, 0, 0, 0, "")
    issues = []
    for line in res.stdout.splitlines():
        try:
            issues.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    files = {i.get("location", {}).get("file", "") for i in issues}
    rule_counts: dict[str, int] = defaultdict(int)
    for i in issues:
        rule_counts[i.get("code", "?")] += 1
    top = ";".join(f"{r}:{c}" for r, c in sorted(rule_counts.items(), key=lambda kv: -kv[1])[:5])
    return LintResult(repo.name, "staticcheck", True, len(issues), 0, len(files), top)


def analyze_repo(repo: Path) -> LintResult:
    lang = detect_repo_language(repo)
    if lang == "javascript":
        return _eslint(repo)
    if lang == "python":
        return _ruff(repo)
    if lang == "go":
        return _staticcheck(repo)
    return LintResult(repo.name, "none", False, 0, 0, 0, "", f"no linter wired for language '{lang}'")


def run_lint_quality(repos: list[Path], out_dir: Path) -> Path:
    # each repo's own lint run is one I/O-bound subprocess call, independent
    # of every other repo -- see core.util.run_concurrent's docstring.
    rows = [asdict(r) for r in run_concurrent(repos, analyze_repo)]
    out_path = out_dir / "lint_quality.csv"
    write_csv(out_path, rows)

    ran = [r for r in rows if r["ran"]]
    write_json(out_dir / "lint_quality_summary.json", {
        "repos_linted": len(ran),
        "repos_skipped": len(rows) - len(ran),
        "skip_reasons": {r["repo"]: r["skip_reason"] for r in rows if not r["ran"]},
        "total_errors": sum(r["error_count"] for r in ran),
        "total_warnings": sum(r["warning_count"] for r in ran),
    })
    return out_path
