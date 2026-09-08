"""Portfolio entrypoint: writes one CSV row per repo, plus a small JSON
summary. write_csv() requires an explicit fieldnames argument (hardened in
d1a06fc) -- passed as the dataclass type here, matching every other
collector's post-hardening call site."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo
from .models import ApiContractResult


def run_api_contract(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "api_contract.csv"
    write_csv(out_path, rows, ApiContractResult)
    write_json(out_dir / "api_contract_summary.json", {
        "repos_total": len(rows),
        "repos_with_spec": sum(1 for r in rows if r["has_spec"]),
        "repos_with_breaking_change_check": sum(1 for r in rows if r["has_breaking_change_check"]),
        "repos_with_contract_test_tooling": sum(1 for r in rows if r["has_contract_test_tooling"]),
        "deprecated_with_sunset_total": sum(r["deprecated_with_sunset_count"] for r in rows),
        "deprecated_without_sunset_total": sum(r["deprecated_without_sunset_count"] for r in rows),
    })
    return out_path
