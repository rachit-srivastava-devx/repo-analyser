"""Cross-repo duplication via jscpd, run once across the whole portfolio
root so it can see duplication *between* repos, not just within one.

The number that matters most for a portfolio isn't the overall duplication
percentage (inflated by legitimate per-project boilerplate) -- it's how much
of the duplication is the *same relative path, byte-for-byte, in more than
one repo*. That is a direct, mechanical measurement of "this should be one
shared package," not an inference.
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import cast

from ..core.lang import JSCPD_FORMAT, detect_portfolio_languages
from ..core.util import run, write_csv, write_json

# jscpd's runtime scales with total code volume, and a portfolio-root scan
# (this module's whole point -- see module docstring) has no natural size
# ceiling. This was bumped once already, 300s -> 900s, after a real run
# against a large Rust+ML portfolio (Principal Engineering, 2026-09-04)
# timed out at 300s -- and then proven insufficient *again* on a second
# real run against the same portfolio (docs/METHODOLOGY.md #30), which was
# still running strong 15+ minutes past the 900s mark. Two hardcoded
# guesses in a row missing is itself the signal: rather than guess a third
# fixed number that the next larger portfolio would just as likely
# outgrow, this is now overridable -- REPO_ANALYSER_JSCPD_TIMEOUT, same
# override-an-environment-specific-default pattern as
# REPO_ANALYSER_NODE_BIN elsewhere in this codebase. Still a hard ceiling
# either way, never unbounded.
DEFAULT_JSCPD_TIMEOUT_S = 900


def _jscpd_timeout() -> int:
    override = os.environ.get("REPO_ANALYSER_JSCPD_TIMEOUT")
    return int(override) if override else DEFAULT_JSCPD_TIMEOUT_S


def _split_repo(path: str) -> tuple[str, str]:
    """'some-repo/scripts/foo.js' -> ('some-repo', 'scripts/foo.js')"""
    if "/" not in path:
        return path, ""
    repo, rel = path.split("/", 1)
    return repo, rel


def run_duplication(portfolio_root: Path, out_dir: Path, min_lines: int = 10, min_tokens: int = 70,
                     repos: list[Path] | None = None) -> Path:
    raw_dir = out_dir / "jscpd_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if repos:
        langs = detect_portfolio_languages(repos)
        formats = sorted({fmt for lang in langs for fmt in JSCPD_FORMAT.get(lang, "").split(",") if fmt})
    else:
        formats = []
    if not formats:
        formats = JSCPD_FORMAT["javascript"].split(",")  # default: this tool's original, JS/TS-only behavior

    # jscpd exits non-zero on finding clones by default; that's expected,
    # not a failure -- see check=False below.
    #
    # NOT passing --no-gitignore (docs/METHODOLOGY.md #36): it was present
    # with zero documented rationale, and real evidence points at it being
    # the actual cause of this module's repeated timeouts (300s -> 900s ->
    # 1800s, all insufficient against the same real portfolio) rather than
    # a genuine "this much real source code takes this long" ceiling --
    # two of that portfolio's own repos' own .gitignore files explicitly
    # exclude multi-gigabyte target/var/vendor directories (Rust build
    # output, runtime logs, vendored deps) that --no-gitignore was forcing
    # jscpd to scan anyway. jscpd's own default already respects
    # .gitignore, which is what real source-only duplication scanning
    # wants; overriding that default needs a real reason, and none survived
    # in this codebase's own decision log.
    run([
        "jscpd", str(portfolio_root),
        "--format", ",".join(formats),
        "--ignore", "**/node_modules/**,**/dist/**,**/build/**,**/.git/**,**/coverage/**,**/.next/**,**/.turbo/**",
        "--min-lines", str(min_lines), "--min-tokens", str(min_tokens),
        "--reporters", "json", "--output", str(raw_dir),
    ], check=False, timeout=_jscpd_timeout())

    report_path = raw_dir / "jscpd-report.json"
    if not report_path.exists():
        raise RuntimeError(f"jscpd did not produce a report at {report_path}")
    import json
    report = json.loads(report_path.read_text())
    duplicates = report.get("duplicates", [])
    stats = report.get("statistics", {}).get("total", {})

    rows = []
    same_path_clusters: dict[str, set[str]] = defaultdict(set)
    cross_repo_lines = 0
    within_repo_lines = 0

    for d in duplicates:
        first = d["firstFile"]["name"]
        second = d["secondFile"]["name"]
        r1, p1 = _split_repo(first)
        r2, p2 = _split_repo(second)
        is_cross = r1 != r2
        lines = d.get("lines", 0)
        if is_cross:
            cross_repo_lines += lines
        else:
            within_repo_lines += lines
        if is_cross and p1 == p2:
            same_path_clusters[p1].update([r1, r2])
        rows.append({
            "repo_a": r1, "path_a": p1, "repo_b": r2, "path_b": p2,
            "is_cross_repo": is_cross, "same_relative_path": p1 == p2,
            "lines": lines, "tokens": d.get("tokens", 0), "format": d.get("format", ""),
        })

    write_csv(out_dir / "duplication_clones.csv", rows,
              fieldnames=["repo_a", "path_a", "repo_b", "path_b", "is_cross_repo",
                          "same_relative_path", "lines", "tokens", "format"])

    cluster_rows = sorted(
        ({"relative_path": p, "repo_count": len(repos), "repos": ";".join(sorted(repos))}
         for p, repos in same_path_clusters.items()),
        key=lambda r: -cast(int, r["repo_count"]),
    )
    write_csv(out_dir / "duplication_shared_path_clusters.csv", cluster_rows,
              fieldnames=["relative_path", "repo_count", "repos"])

    write_json(out_dir / "duplication_summary.json", {
        "portfolio_stats": stats,
        "total_clone_pairs": len(duplicates),
        "cross_repo_clone_pairs": sum(1 for r in rows if r["is_cross_repo"]),
        "within_repo_clone_pairs": sum(1 for r in rows if not r["is_cross_repo"]),
        "cross_repo_duplicated_lines": cross_repo_lines,
        "within_repo_duplicated_lines": within_repo_lines,
        "identical_relative_path_clusters": len(same_path_clusters),
        "identical_relative_path_files_max_repo_count": max(
            (cast(int, r["repo_count"]) for r in cluster_rows), default=0),
    })
    return out_dir / "duplication_clones.csv"
