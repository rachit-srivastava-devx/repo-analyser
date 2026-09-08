"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary. write_csv() requires an explicit fieldnames argument -- passed as
the dataclass type here, matching every other collector's post-hardening
call site (see api_contract/runner.py's own docstring)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import MonorepoToolingResult


def run_monorepo_tooling(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "monorepo_tooling.csv"
    write_csv(out_path, rows, MonorepoToolingResult)
    write_json(out_dir / "monorepo_tooling_summary.json", {
        "repos_total": len(rows),
        "repos_with_any_orchestrator": sum(1 for r in rows if r["orchestrator_count"] > 0),
        "repos_with_nx": sum(1 for r in rows if r["nx_present"]),
        "repos_with_turbo": sum(1 for r in rows if r["turbo_present"]),
        "repos_with_bazel": sum(1 for r in rows if r["bazel_present"]),
        "repos_with_buck2": sum(1 for r in rows if r["buck_present"]),
        "repos_with_pants": sum(1 for r in rows if r["pants_present"]),
        "repos_with_multiple_orchestrators": sum(1 for r in rows if r["orchestrator_count"] > 1),
    })
    return out_path
