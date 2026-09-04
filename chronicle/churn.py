"""Code-maat wrapper: churn (revisions), temporal/logical coupling, and code
age, straight from git log -- the "Your Code as a Crime Scene" methodology
(Tornhill). code-maat is a real external tool (Clojure, run as a standalone
jar); this module's only job is to feed it the git log format it expects and
parse its CSV back into ours.
"""
from __future__ import annotations

from pathlib import Path

from .util import run, write_csv

_THIS_DIR = Path(__file__).resolve().parent.parent
CODE_MAAT_JAR = _THIS_DIR / "tools" / "code-maat.jar"


def _write_maat_log(repo: Path, out_file: Path) -> None:
    res = run(["git", "log", "--all", "--numstat", "--date=short",
               "--pretty=format:--%h--%ad--%an", "--no-renames"], cwd=repo)
    out_file.write_text(res.stdout)


def _run_maat(log_file: Path, analysis: str) -> list[dict]:
    res = run(["java", "-jar", str(CODE_MAAT_JAR), "-l", str(log_file), "-c", "git2", "-a", analysis],
              check=False, timeout=300)
    if res.returncode != 0:
        raise RuntimeError(f"code-maat -a {analysis} failed: {res.stderr[:500]}")
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    if not lines:
        return []
    header = lines[0].split(",")
    return [dict(zip(header, l.split(","))) for l in lines[1:]]


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
    write_csv(rev_path, all_revisions, fieldnames=["repo", "entity", "n-revs"] if all_revisions else None)
    coup_path = out_dir / "churn_coupling.csv"
    write_csv(coup_path, all_coupling,
              fieldnames=["repo", "entity", "coupled", "degree", "average-revs"] if all_coupling else None)

    if errors:
        from .util import write_json
        write_json(out_dir / "churn_errors.json", errors)
    return rev_path, coup_path
