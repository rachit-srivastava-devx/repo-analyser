"""Complexity + hotspots: lizard for per-function cyclomatic complexity,
joined against code-maat's churn (n-revs) to compute Tornhill's hotspot
score: hotspot = total_complexity(file) x n_revisions(file). A file that is
complex but never changes is low risk; a file that changes constantly but is
trivial is low risk. The product is where defects concentrate.

lizard's --csv columns (no header row emitted): nloc, ccn, token_count,
param_count, length, location, filename, function_name, long_name,
start_line, end_line.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from ..core.lang import EXCLUDE_DIR_PARTS
from ..core.util import run, run_concurrent, write_csv, write_json

# core.lang.EXCLUDE_DIR_PARTS, in lizard's glob-pattern form for its `-x`
# flag -- was its own separately-maintained 6-entry list here (missing
# .turbo/venv/.venv/__pycache__/vendor/target, all present in the shared
# set) until the two drifted enough that a Rust repo's multi-GB `target/`
# build directory would have gone straight into a complexity scan.
EXCLUDES = [f"*/{d}/*" for d in EXCLUDE_DIR_PARTS]


def _norm(path: str) -> str:
    return path[2:] if path.startswith("./") else path


def analyze_repo_functions(repo: Path) -> list[dict]:
    cmd = ["lizard", ".", "--csv"]
    for e in EXCLUDES:
        cmd += ["-x", e]
    res = run(cmd, cwd=repo, check=False, timeout=300)
    # lizard exits non-zero when it finds functions over its default
    # complexity threshold (that's its "warning" signal, not a tool failure)
    if not res.stdout.strip():
        raise RuntimeError(f"lizard produced no output for {repo.name}: {res.stderr[:500]}")
    reader = csv.reader(io.StringIO(res.stdout))
    rows = []
    for cols in reader:
        if len(cols) < 11:
            continue
        rows.append({
            "repo": repo.name, "nloc": int(cols[0]), "ccn": int(cols[1]),
            "tokens": int(cols[2]), "params": int(cols[3]), "length": int(cols[4]),
            "file": _norm(cols[6]), "function": cols[7], "start_line": cols[9], "end_line": cols[10],
        })
    return rows


def aggregate_by_file(function_rows: list[dict]) -> list[dict]:
    agg: dict[tuple[str, str], dict] = {}
    for r in function_rows:
        key = (r["repo"], r["file"])
        if key not in agg:
            agg[key] = {"repo": r["repo"], "file": r["file"], "total_ccn": 0, "max_ccn": 0,
                        "function_count": 0, "total_nloc": 0}
        a = agg[key]
        a["total_ccn"] += r["ccn"]
        a["max_ccn"] = max(a["max_ccn"], r["ccn"])
        a["function_count"] += 1
        a["total_nloc"] += r["nloc"]
    return list(agg.values())


def _complexity_scan_one(r: Path) -> tuple[list[dict], dict[str, str]]:
    try:
        return list(analyze_repo_functions(r)), {}
    except RuntimeError as e:
        return [], {r.name: str(e)}


def run_complexity(repos: list[Path], out_dir: Path, churn_csv: Path | None = None) -> Path:
    all_functions: list[dict] = []
    errors: dict[str, str] = {}
    # each repo's own lizard scan is one I/O-bound subprocess call -- see
    # core.util.run_concurrent's docstring.
    for functions, repo_errors in run_concurrent(repos, _complexity_scan_one):
        all_functions.extend(functions)
        errors.update(repo_errors)

    func_path = out_dir / "complexity_functions.csv"
    write_csv(func_path, all_functions,
              fieldnames=["repo", "file", "function", "nloc", "ccn", "tokens", "params",
                          "length", "start_line", "end_line"] if all_functions else None)

    file_agg = aggregate_by_file(all_functions)

    churn_by_key: dict[tuple[str, str], int] = {}
    if churn_csv and churn_csv.exists():
        with open(churn_csv) as f:
            for row in csv.DictReader(f):
                try:
                    churn_by_key[(row["repo"], row["entity"])] = int(row["n-revs"])
                except (KeyError, ValueError):
                    continue

    for a in file_agg:
        n_revs = churn_by_key.get((a["repo"], a["file"]), 0)
        a["n_revs"] = n_revs
        a["hotspot_score"] = a["total_ccn"] * n_revs

    file_agg.sort(key=lambda a: -a["hotspot_score"])
    hotspot_path = out_dir / "complexity_hotspots.csv"
    write_csv(hotspot_path, file_agg,
              fieldnames=["repo", "file", "total_ccn", "max_ccn", "function_count",
                          "total_nloc", "n_revs", "hotspot_score"] if file_agg else None)

    if errors:
        write_json(out_dir / "complexity_errors.json", errors)
    return hotspot_path
