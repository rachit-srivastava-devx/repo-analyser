"""Defect escape rate via the SZZ algorithm (Sliwerski/Zimmermann/Zeller 2005),
implemented directly on top of PyDriller + `git blame` -- the same technique
SZZUnleashed uses, reimplemented here so it shares the ontology's fix-commit
identification and this tool's output format.

Algorithm, precisely:
  1. A "fix commit" is any non-merge commit ontology.py classifies as
     bug_fix or revert.
  2. For each fix commit F with parent P, for each modified file, take the
     *deleted/modified* line numbers in P's version (pure additions carry no
     blame target and are excluded -- see `pure_addition_fixes` in the
     summary, reported not hidden).
  3. `git blame P -- file` attributes each of those line numbers to the
     commit that last touched them. That commit is a bug-introducing commit.
  4. escape_rate(month M) = |commits authored in M later blamed by a fix
     landing within WINDOW_DAYS| / |all non-merge commits authored in M|.
  5. fix_latency = fix_commit.author_date - introducing_commit.author_date.

Known limitation, stated rather than hidden: this is line-based SZZ without
the "meta-change" and "line-mapping" refinements from SZZ RA/SZZ Unleashed
(which correct for lines that moved rather than changed, and filter
cosmetic-only reformatting). Expect this to inflate attribution to
reformatting/rename-adjacent commits by some margin -- quantified in the
audit pass, not assumed away.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from pydriller import Repository

from ..core.util import run, write_csv, write_json
from .ontology import classify_commit

WINDOW_DAYS = 365
BLAME_LINE_RE = re.compile(r"^\^?([0-9a-f]{7,40})\s")


@dataclass
class Escape:
    repo: str
    fix_sha: str
    fix_date: str
    file: str
    introducing_sha: str
    introducing_date: str
    latency_days: int


def _blame_map(repo: Path, parent_sha: str, file_path: str) -> dict[int, str]:
    """line number (1-indexed, in parent_sha's version of file_path) -> commit sha"""
    res = run(["git", "blame", "--line-porcelain", parent_sha, "--", file_path],
              cwd=repo, check=False)
    if res.returncode != 0:
        return {}
    mapping: dict[int, str] = {}
    line_no = 0
    current_sha = None
    for line in res.stdout.splitlines():
        m = BLAME_LINE_RE.match(line)
        if m and len(m.group(1)) >= 7 and not line.startswith(("author ", "committer ", "summary ")):
            # a porcelain header line starts with "<sha> <orig-line> <final-line> [<num-lines>]"
            parts = line.split()
            if len(parts) >= 3 and re.fullmatch(r"[0-9a-f]{7,40}", parts[0]):
                current_sha = parts[0]
                try:
                    line_no = int(parts[2])
                except ValueError:
                    continue
                mapping[line_no] = current_sha
    return mapping


def _fix_commits(repo: Path) -> list:
    fixes = []
    for commit in Repository(str(repo), only_no_merge=True).traverse_commits():
        touched = [m.new_path or m.old_path for m in commit.modified_files if (m.new_path or m.old_path)]
        leaf, _rule = classify_commit(commit.msg.splitlines()[0] if commit.msg else "", touched)
        if leaf in ("bug_fix", "revert"):
            fixes.append(commit)
    return fixes


def analyze_repo(repo: Path) -> tuple[list[Escape], dict]:
    escapes: list[Escape] = []
    pure_addition_fixes = 0
    unattributed_hunks = 0
    total_fix_commits = 0

    for commit in _fix_commits(repo):
        total_fix_commits += 1
        parent = commit.parents[0] if commit.parents else None
        if parent is None:
            continue
        any_attributed = False
        for mf in commit.modified_files:
            old_path = mf.old_path
            if not old_path:
                continue
            deleted_lines = [ln for ln, _content in (mf.diff_parsed or {}).get("deleted", [])]
            if not deleted_lines:
                continue
            blame = _blame_map(repo, parent, old_path)
            if not blame:
                continue
            seen_introducers: set[str] = set()
            for ln in deleted_lines:
                sha = blame.get(ln)
                if not sha or sha == commit.hash[: len(sha)] or sha in seen_introducers:
                    continue
                seen_introducers.add(sha)
                intro_res = run(["git", "show", "-s", "--format=%ad", "--date=iso-strict", sha],
                                 cwd=repo, check=False)
                if intro_res.returncode != 0 or not intro_res.stdout.strip():
                    unattributed_hunks += 1
                    continue
                intro_date = datetime.fromisoformat(intro_res.stdout.strip())
                fix_date = commit.author_date
                latency = (fix_date.astimezone(intro_date.tzinfo) - intro_date).days
                if latency < 0:
                    continue
                any_attributed = True
                escapes.append(Escape(
                    repo=repo.name, fix_sha=commit.hash[:10], fix_date=fix_date.isoformat(),
                    file=old_path, introducing_sha=sha[:10], introducing_date=intro_date.isoformat(),
                    latency_days=latency,
                ))
        if not any_attributed:
            pure_addition_fixes += 1

    stats = {
        "total_fix_commits": total_fix_commits,
        "pure_addition_or_unattributed_fixes": pure_addition_fixes,
        "unattributed_hunks": unattributed_hunks,
        "escapes_found": len(escapes),
    }
    return escapes, stats


def _month(iso_date: str) -> str:
    return iso_date[:7]


def run_escape(repos: list[Path], out_dir: Path) -> Path:
    all_escapes: list[Escape] = []
    per_repo_stats = {}
    for r in repos:
        escapes, stats = analyze_repo(r)
        all_escapes.extend(escapes)
        per_repo_stats[r.name] = stats

    rows = [asdict(e) for e in all_escapes]
    out_path = out_dir / "escapes.csv"
    write_csv(out_path, rows, fieldnames=list(Escape.__annotations__.keys()) if rows else None)

    # monthly escape rate needs the denominator (all non-merge commits per month per repo),
    # computed once here from git log directly rather than re-walking PyDriller.
    commits_per_month: dict[str, int] = defaultdict(int)
    escaped_intro_per_month: dict[str, set[str]] = defaultdict(set)
    for r in repos:
        res = run(["git", "log", "--all", "--no-merges", "--format=%H\x01%ad", "--date=iso-strict"], cwd=r)
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            sha, date = line.split("\x01")
            commits_per_month[_month(date)] += 1
    for e in all_escapes:
        if e.latency_days <= WINDOW_DAYS:
            escaped_intro_per_month[_month(e.introducing_date)].add(e.introducing_sha)

    monthly = []
    for month in sorted(commits_per_month):
        n_commits = commits_per_month[month]
        n_escaped = len(escaped_intro_per_month.get(month, set()))
        monthly.append({
            "month": month, "commits": n_commits, "escaped_introductions": n_escaped,
            "escape_rate_12mo": round(n_escaped / n_commits, 4) if n_commits else 0.0,
        })
    write_csv(out_dir / "escape_monthly.csv", monthly)

    latencies = sorted(e.latency_days for e in all_escapes)
    def pct(p):
        if not latencies:
            return None
        idx = min(len(latencies) - 1, int(len(latencies) * p))
        return latencies[idx]

    write_json(out_dir / "escape_summary.json", {
        "per_repo_fix_commit_stats": per_repo_stats,
        "total_escapes_attributed": len(all_escapes),
        "latency_days_median": pct(0.5), "latency_days_p90": pct(0.9), "latency_days_p10": pct(0.1),
        "window_days": WINDOW_DAYS,
    })
    return out_path
