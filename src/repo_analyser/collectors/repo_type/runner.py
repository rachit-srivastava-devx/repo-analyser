from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv, write_json
from .analyze import analyze_repo


def run_repo_type(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r, repos)) for r in repos]
    out_path = out_dir / "repo_type.csv"
    write_csv(out_path, rows)
    primary_counts = Counter(r["primary_type"] for r in rows)
    content_counts: Counter[str] = Counter()
    for r in rows:
        for c in r["content_types"].split(";"):
            if c:
                content_counts[c] += 1
    write_json(out_dir / "repo_type_summary.json", {
        "repos_total": len(rows),
        "primary_type_counts": dict(primary_counts),
        "content_type_counts": dict(content_counts),
    })
    return out_path
