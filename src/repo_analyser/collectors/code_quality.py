"""Keyless code-quality score: a SonarQube Quality Gate stand-in that
needs no running server. SonarQube Community Edition itself needs a live
Java/Docker server, which doesn't fit this tool's single-CLI-invocation
architecture (docs/METHODOLOGY.md).

Python: radon's Maintainability Index -- a real, published formula
(Halstead Volume + Cyclomatic Complexity + lines of code, 0-100, the same
shape of number a SonarQube quality gate reports), via radon's own Python
API directly rather than shelling out to a CLI: it's a real, pinned
dependency (verified installing and running cleanly under this project's
own Python version before adding it, not assumed), so no subprocess, no
PATH-resolution version-drift risk the way lizard/jscpd/dependency-cruiser
have. Grade bands (A/B/C) are radon's own documented convention, not
invented here.

Scope, stated honestly: Python only for now. A JS/TS equivalent
(escomplex/typhonjs-escomplex-style Maintainability Index) needs its own
verification pass for a currently-maintained tool before it's added --
checked at the same time as this module (docs/METHODOLOGY.md #37) and
found wanting, not silently skipped.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from radon.metrics import mi_visit

from ..core.lang import EXCLUDE_DIR_PARTS, detect_repo_language
from ..core.util import write_csv, write_json


def _mi_grade(score: float) -> str:
    if score >= 20:
        return "A"
    if score >= 10:
        return "B"
    return "C"


@dataclass
class CodeQualityResult:
    repo: str
    language: str
    files_analyzed: int
    files_skipped: int
    mean_maintainability_index: float
    grade: str
    lowest_file: str
    lowest_file_mi: float
    ran: bool
    skip_reason: str = ""


def _python_files(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*.py")
            if p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.parts)]


def analyze_repo(repo: Path) -> CodeQualityResult:
    lang = detect_repo_language(repo)
    if lang != "python":
        return CodeQualityResult(repo.name, lang, 0, 0, 0.0, "", "", 0.0, False,
                                  skip_reason=f"language '{lang}' not supported by code_quality (supported: "
                                              f"['python'])")
    # No "no Python files found" branch: detect_repo_language and
    # _python_files both walk the same repo.rglob() with the identical
    # EXCLUDE_DIR_PARTS filter, so `lang == "python"` (meaning a .py file
    # was already counted as the dominant extension) makes that list
    # non-empty by construction -- confirmed by a real failing test, not
    # assumed; a dead branch here would just be an unreachable illusion of
    # handling a case that can't occur.
    files = _python_files(repo)

    scores: dict[str, float] = {}
    skipped = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped += 1
            continue
        try:
            mi = mi_visit(text, True)
        except SyntaxError:
            skipped += 1
            continue
        if mi is not None:
            scores[str(f.relative_to(repo))] = mi

    if not scores:
        return CodeQualityResult(repo.name, lang, 0, skipped, 0.0, "", "", 0.0, False,
                                  skip_reason=f"no file produced a valid MI score ({skipped} skipped)")

    mean_mi = round(sum(scores.values()) / len(scores), 1)
    lowest_file, lowest_mi = min(scores.items(), key=lambda kv: kv[1])
    return CodeQualityResult(
        repo=repo.name, language=lang, files_analyzed=len(scores), files_skipped=skipped,
        mean_maintainability_index=mean_mi, grade=_mi_grade(mean_mi),
        lowest_file=lowest_file, lowest_file_mi=round(lowest_mi, 1), ran=True,
    )


def run_code_quality(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "code_quality.csv"
    write_csv(out_path, rows, fieldnames=CodeQualityResult)
    ran = [r for r in rows if r["ran"]]
    write_json(out_dir / "code_quality_summary.json", {
        "repos_analyzed": len(ran),
        "repos_skipped": len(rows) - len(ran),
        "mean_maintainability_index": round(sum(r["mean_maintainability_index"] for r in ran) / len(ran), 1)
        if ran else None,
        "grade_distribution": {g: sum(1 for r in ran if r["grade"] == g) for g in ("A", "B", "C")},
    })
    return out_path
