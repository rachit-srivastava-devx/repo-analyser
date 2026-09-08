"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary. write_csv() requires an explicit fieldnames argument (hardened in
d1a06fc) -- passed as the dataclass type here, matching every other
collector's post-hardening call site."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import DesignDocsResult


def run_design_docs(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "design_docs.csv"
    write_csv(out_path, rows, DesignDocsResult)

    accepted_rows = [r for r in rows if r["adr_status_accepted_count"] > 0]
    write_json(out_dir / "design_docs_summary.json", {
        "repos_total": len(rows),
        "repos_with_hld": sum(1 for r in rows if r["has_hld"]),
        "repos_with_adr_dir": sum(1 for r in rows if r["has_adr_dir"]),
        "repos_with_runbook": sum(1 for r in rows if r["has_runbook"]),
        "adr_file_total": sum(r["adr_file_count"] for r in rows),
        "adr_with_standard_sections_total": sum(r["adr_with_standard_sections_count"] for r in rows),
        "adr_reversibility_tagged_total": sum(r["adr_reversibility_tagged_count"] for r in rows),
        "repos_with_post_acceptance_adr_modification": sum(
            1 for r in accepted_rows if r["adr_modified_after_acceptance_count"] > 0
        ),
    })
    return out_path
