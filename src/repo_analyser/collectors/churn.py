"""Code-maat wrapper: churn (revisions), temporal/logical coupling, and code
age, straight from git log -- the "Your Code as a Crime Scene" methodology
(Tornhill). code-maat is a real external tool (Clojure, run as a standalone
jar); this module's only job is to feed it the git log format it expects and
parse its CSV back into ours.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..core.util import repo_root, run, write_csv, write_json


def _code_maat_jar() -> Path:
    """REPO_ANALYSER_TOOLS_DIR overrides the default tools/ location
    (repo_root()/tools) -- same override pattern as REPO_ANALYSER_NODE_BIN
    in testquality.py/mutation.py."""
    tools_dir = Path(os.environ["REPO_ANALYSER_TOOLS_DIR"]) if os.environ.get("REPO_ANALYSER_TOOLS_DIR") \
        else repo_root() / "tools"
    return tools_dir / "code-maat.jar"


def _write_maat_log(repo: Path, out_file: Path) -> None:
    res = run(["git", "log", "--all", "--numstat", "--date=short",
               "--pretty=format:--%h--%ad--%an", "--no-renames"], cwd=repo)
    out_file.write_text(res.stdout)


def _run_maat(log_file: Path, analysis: str) -> list[dict]:
    res = run(["java", "-jar", str(_code_maat_jar()), "-l", str(log_file), "-c", "git2", "-a", analysis],
              check=False, timeout=300)
    if res.returncode != 0:
        raise RuntimeError(f"code-maat -a {analysis} failed: {res.stderr[:500]}")
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","), strict=True)) for line in lines[1:]]


def analyze_repo(repo: Path, tmp_dir: Path) -> tuple[list[dict], list[dict]]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    log_file = tmp_dir / f"{repo.name}.maatlog"
    _write_maat_log(repo, log_file)

    revisions = _run_maat(log_file, "revisions")
    for row in revisions:
        row["repo"] = repo.name

    coupling = _run_maat(log_file, "coupling")
    for row in coupling:
        row["repo"] = repo.name

    return revisions, coupling


def run_churn(repos: list[Path], out_dir: Path, tmp_dir: Path) -> tuple[Path, Path]:
    all_revisions: list[dict] = []
    all_coupling: list[dict] = []
    errors: dict[str, str] = {}
    for r in repos:
        try:
            revs, coup = analyze_repo(r, tmp_dir)
            all_revisions.extend(revs)
            all_coupling.extend(coup)
        except RuntimeError as e:
            errors[r.name] = str(e)

    rev_path = out_dir / "churn_revisions.csv"
    write_csv(rev_path, all_revisions, fieldnames=["repo", "entity", "n-revs"])
    coup_path = out_dir / "churn_coupling.csv"
    write_csv(coup_path, all_coupling,
              fieldnames=["repo", "entity", "coupled", "degree", "average-revs"])

    if errors:
        write_json(out_dir / "churn_errors.json", errors)
    return rev_path, coup_path
