"""Portfolio-level entrypoint: writes one CSV row per repo."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ...core.util import write_csv
from .analyze import analyze_repo


def run_agent_skill_quality(repos: list[Path], out_dir: Path) -> Path:
    rows = [asdict(analyze_repo(r)) for r in repos]
    out_path = out_dir / "agent_skill_quality.csv"
    write_csv(out_path, rows)
    return out_path
