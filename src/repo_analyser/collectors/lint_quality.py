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
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from ..core.lang import EXCLUDE_DIR_PARTS, EXT_TO_LANG, detect_repo_language
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
    # Lint-suppression-marker density, independent of whether `linter` above
    # actually ran -- a repo-content scan (see `_suppression_stats`), not a
    # linter-output parse. One count/kloc/density triple per language, never
    # collapsed into a single repo-wide number: a polyglot repo's Python
    # density would otherwise be diluted (or hidden) by its JS line count.
    python_suppression_count: int = 0
    python_kloc: float = 0.0
    python_suppression_density: float = 0.0
    javascript_suppression_count: int = 0
    javascript_kloc: float = 0.0
    javascript_suppression_density: float = 0.0
    go_suppression_count: int = 0
    go_kloc: float = 0.0
    go_suppression_density: float = 0.0


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


# Lint-suppression markers this scan recognizes -- one convention per
# ecosystem, matched as a plain regex over each file's raw text rather than
# a real parser for any of the three languages. A marker matched inside a
# string literal, or a comment *about* suppression rather than an actual
# directive, is a stated, accepted false-positive risk -- the same tradeoff
# RUFF_SUMMARY_RE above already makes parsing ruff's own text output, and
# building a real per-language parser to close it is out of scope here.
# eslint-disable: matches inside both `// eslint-disable...` and
# `/* eslint-disable... */` without encoding either comment delimiter --
# the marker text itself is what's counted, so one pattern covers both.
PY_SUPPRESSION_RE = re.compile(r"#\s*noqa\b|#\s*type:\s*ignore\b")
JS_SUPPRESSION_RE = re.compile(r"eslint-disable")
GO_SUPPRESSION_RE = re.compile(r"//nolint\b")

# core.lang.EXT_TO_LANG's own JS/TS extension family -- reused rather than
# re-listing .ts/.tsx/.js/.jsx/.mjs/.cjs a second time here.
JS_SUPPRESSION_EXTS = {ext for ext, lang in EXT_TO_LANG.items() if lang == "javascript"}


@dataclass
class _LangSuppression:
    count: int
    kloc: float
    density: float


def _suppression_stats(repo: Path) -> dict[str, _LangSuppression]:
    """Lint-suppression density per language: raw marker count, that
    language's own KLOC (thousands of lines, across its own files only),
    and count/KLOC -- for Python, JS/TS, and Go. Normalized per that same
    language's KLOC, never total-repo KLOC: a repo that's 90% JS by volume
    with one heavily-noqa'd Python script would look artificially clean
    under a repo-wide denominator.

    Walks every file under `repo` once, skipping `EXCLUDE_DIR_PARTS`
    (vendored/build/venv dirs every other collector already excludes) --
    a plain filesystem walk, same as `detect_repo_language`, never
    `git ls-files` (nothing in this codebase shells out to git for a file
    list). Zero suppressions, or zero lines of a language, are legitimate
    results (density 0.0), not errors -- only the KLOC denominator being
    zero is guarded (would otherwise raise ZeroDivisionError).

    Returns one `_LangSuppression` per language, keyed "python"/
    "javascript"/"go" -- a small typed result rather than a bare
    `dict[str, int | float]`, so the caller can pass its fields into
    `dataclasses.replace(...)` as explicit, individually-typed keyword
    arguments (mypy checks a `**`-splatted heterogeneous dict against
    *every* field of the target dataclass, not just the ones a caller
    intends to set -- explicit keywords are what actually type-checks).
    """
    lines = {"python": 0, "javascript": 0, "go": 0}
    hits = {"python": 0, "javascript": 0, "go": 0}
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.suffix == ".py":
            file_lang, pattern = "python", PY_SUPPRESSION_RE
        elif p.suffix in JS_SUPPRESSION_EXTS:
            file_lang, pattern = "javascript", JS_SUPPRESSION_RE
        elif p.suffix == ".go":
            file_lang, pattern = "go", GO_SUPPRESSION_RE
        else:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines[file_lang] += len(text.splitlines())
        hits[file_lang] += len(pattern.findall(text))

    stats: dict[str, _LangSuppression] = {}
    for file_lang in ("python", "javascript", "go"):
        kloc = lines[file_lang] / 1000.0
        density = round(hits[file_lang] / kloc, 3) if kloc > 0 else 0.0
        stats[file_lang] = _LangSuppression(count=hits[file_lang], kloc=round(kloc, 3), density=density)
    return stats


def analyze_repo(repo: Path) -> LintResult:
    lang = detect_repo_language(repo)
    if lang == "javascript":
        result = _eslint(repo)
    elif lang == "python":
        result = _ruff(repo)
    elif lang == "go":
        result = _staticcheck(repo)
    else:
        result = LintResult(repo.name, "none", False, 0, 0, 0, "", f"no linter wired for language '{lang}'")
    # Suppression-marker density is a repo-content scan, independent of
    # which linter (if any) is wired for this repo's *dominant* language --
    # a repo whose dominant language has no linter here can still have,
    # e.g., a handful of Python files with real noqa-style suppressions.
    stats = _suppression_stats(repo)
    py, js, go = stats["python"], stats["javascript"], stats["go"]
    return replace(
        result,
        python_suppression_count=py.count, python_kloc=py.kloc, python_suppression_density=py.density,
        javascript_suppression_count=js.count, javascript_kloc=js.kloc, javascript_suppression_density=js.density,
        go_suppression_count=go.count, go_kloc=go.kloc, go_suppression_density=go.density,
    )


def run_lint_quality(repos: list[Path], out_dir: Path) -> Path:
    # each repo's own lint run is one I/O-bound subprocess call, independent
    # of every other repo -- see core.util.run_concurrent's docstring.
    rows = [asdict(r) for r in run_concurrent(repos, analyze_repo)]
    out_path = out_dir / "lint_quality.csv"
    write_csv(out_path, rows, fieldnames=LintResult)

    ran = [r for r in rows if r["ran"]]
    write_json(out_dir / "lint_quality_summary.json", {
        "repos_linted": len(ran),
        "repos_skipped": len(rows) - len(ran),
        "skip_reasons": {r["repo"]: r["skip_reason"] for r in rows if not r["ran"]},
        "total_errors": sum(r["error_count"] for r in ran),
        "total_warnings": sum(r["warning_count"] for r in ran),
    })
    return out_path
