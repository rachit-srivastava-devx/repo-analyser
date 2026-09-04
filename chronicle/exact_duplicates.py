"""Exact-content duplicate files across a portfolio, by sha256 -- a second,
independent measurement from jscpd's block-level clone detection.

This exists because jscpd's clustering answers "do these files share a
duplicated block," which two files can satisfy while still differing
elsewhere (e.g. shared boilerplate plus real per-tenant customization). This
module answers a stricter, unambiguous question: is the *entire file*
byte-for-byte identical. Report both; do not let one stand in for the other.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from .util import write_csv, write_json

EXCLUDE_DIRS = {"node_modules", "dist", "build", ".git", "coverage", ".next", ".turbo"}
INCLUDE_EXT = {".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml",
               ".py", ".go", ".java", ".kt", ".rb", ".rs"}
# noisy, expected-to-be-per-repo files that would pollute the signal if included
EXCLUDE_BASENAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}


def _iter_files(repo: Path):
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix not in INCLUDE_EXT or p.name in EXCLUDE_BASENAMES:
            continue
        yield p


def run_exact_duplicates(repos: list[Path], out_dir: Path) -> Path:
    # hash -> list of (repo_name, relative_path)
    by_hash: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for repo in repos:
        for f in _iter_files(repo):
            try:
                data = f.read_bytes()
            except OSError:
                continue
            if not data.strip():
                continue
            h = hashlib.sha256(data).hexdigest()
            by_hash[h].append((repo.name, str(f.relative_to(repo))))

    # Only keep hashes that appear in >1 distinct repo -- same-repo dupes are a different question.
    cross_repo_groups = []
    for h, locations in by_hash.items():
        repos_involved = {r for r, _ in locations}
        if len(repos_involved) > 1:
            cross_repo_groups.append({
                "sha256": h[:16],
                "repo_count": len(repos_involved),
                "instance_count": len(locations),
                "relative_paths": ";".join(sorted({p for _, p in locations}))[:300],
                "repos": ";".join(sorted(repos_involved)),
            })

    cross_repo_groups.sort(key=lambda g: -g["repo_count"])
    out_path = out_dir / "exact_duplicate_files.csv"
    write_csv(out_path, cross_repo_groups,
              fieldnames=["sha256", "repo_count", "instance_count", "relative_paths", "repos"]
              if cross_repo_groups else None)

    single_path_groups = [g for g in cross_repo_groups if ";" not in g["relative_paths"]]
    write_json(out_dir / "exact_duplicate_summary.json", {
        "total_files_scanned": sum(len(v) for v in by_hash.values()),
        "cross_repo_identical_groups": len(cross_repo_groups),
        "cross_repo_identical_same_path_groups": len(single_path_groups),
        "max_repo_count_for_one_file": max((g["repo_count"] for g in cross_repo_groups), default=0),
        "total_repos_in_portfolio": len(repos),
    })
    return out_path
