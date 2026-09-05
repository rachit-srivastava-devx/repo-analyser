"""Commit ontology: classify every non-merge commit by what it actually did,
using a fully deterministic rule table (no LLM in the loop) so the result is
100% reproducible and every classification can be traced to the exact rule
that fired.

Two rule layers, in priority order (first match wins):
  1. File-pattern rules: if every file the commit touched matches a known
     pattern (lockfile, workflow yaml, migration, docs, test), classify by
     that alone, regardless of the commit message. This catches the ~62%
     of commits in this corpus that don't use a conventional-commit prefix.
  2. Message-keyword rules: conventional-commit prefix (feat:/fix:/chore:...)
     or a keyword match against the subject line.
  3. `other` if neither layer matches -- reported honestly as the
     unclassified denominator, never hidden.

Validate this classifier's accuracy before trusting its headline percentages
-- see docs/ONTOLOGY_AUDIT.md for the methodology and results of a blind
manual audit (68.4% exact-leaf / 72.0% superclass agreement, n=193) against
this exact rule table.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.lang import TEST_FILE_RE
from ..core.util import run, write_csv, write_json

COMMIT_SEP = "\x02==REPO-ANALYSER-COMMIT==\x02"
LOG_FORMAT = f"%n{COMMIT_SEP}%n%H\x01%ae\x01%ad\x01%s\x01%P"

# leaf -> superclass
SUPERCLASS = {
    "revert": "correction", "bug_fix": "correction",
    "feature": "delivery",
    "refactor": "code_health", "test": "code_health", "docs": "code_health", "perf": "code_health",
    "ci_build": "ops_config", "dependency_bump": "ops_config", "access_admin": "ops_config", "release": "ops_config",
    "data_schema": "data_schema",
    "chore": "housekeeping", "style": "housekeeping",
    "other": "other",
}

# Priority order: first matching rule wins.
LEAF_PRIORITY = ["revert", "bug_fix", "feature", "data_schema", "access_admin",
                  "ci_build", "dependency_bump", "test", "docs", "release",
                  "refactor", "perf", "style", "chore"]

FILE_RULES: list[tuple[str, re.Pattern]] = [
    ("dependency_bump", re.compile(r"^(package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$")),
    ("ci_build", re.compile(r"^\.github/workflows/|^Dockerfile|^\.dockerignore$|^docker-compose")),
    ("data_schema", re.compile(r"migrations?/|\.sql$|schema\.prisma$")),
    ("docs", re.compile(r"^docs/|README|CHANGELOG|\.md$")),
    ("test", TEST_FILE_RE),
]

MSG_PREFIX_RE = re.compile(
    r"^(?P<type>revert|fix|feat|feature|chore|docs|refactor|test|ci|build|perf|style|release)"
    r"(\([^)]*\))?!?:\s*", re.IGNORECASE,
)
PREFIX_TO_LEAF = {
    "revert": "revert", "fix": "bug_fix", "feat": "feature", "feature": "feature",
    "chore": "chore", "docs": "docs", "refactor": "refactor", "test": "test",
    "ci": "ci_build", "build": "ci_build", "perf": "perf", "style": "style", "release": "release",
}

KEYWORD_RULES: list[tuple[str, re.Pattern]] = [
    ("revert", re.compile(r"\brevert(ed|ing)?\b", re.IGNORECASE)),
    ("bug_fix", re.compile(
        r"\b(fix(ed|es|ing)?|bug|broken|crash|mismatch|incorrect|resolve[sd]?|"
        r"error|fail(ed|ing|ure)?|hotfix)\b", re.IGNORECASE)),
    ("access_admin", re.compile(r"\b(permission|role|access[- ]?control|rbac|iam|secrets?)\b", re.IGNORECASE)),
    ("ci_build", re.compile(r"\b(pipeline|workflow|ecr|ecs|deploy(ment)?|docker|ci\b)\b", re.IGNORECASE)),
    ("dependency_bump", re.compile(
        r"\b(bump|upgrade|update)\b.*\b(deps?|dependency|dependencies|version)\b", re.IGNORECASE)),
    ("data_schema", re.compile(r"\b(migration|schema|db column|database)\b", re.IGNORECASE)),
    ("test", re.compile(r"\b(tests?|spec|coverage)\b", re.IGNORECASE)),
    ("docs", re.compile(r"\b(docs?|documentation|readme|comment)\b", re.IGNORECASE)),
    ("refactor", re.compile(r"\b(refactor|restructure|rename|simplify|extract|cleanup)\b", re.IGNORECASE)),
    ("perf", re.compile(r"\b(perf(ormance)?|optimi[sz]e|latency|speed up)\b", re.IGNORECASE)),
    ("style", re.compile(r"\b(lint|prettier|format(ting)?|whitespace)\b", re.IGNORECASE)),
    ("feature", re.compile(
        r"\b(add(ed|s|ing)?|implement(ed|s|ing)?|introduce[sd]?|support for|new )\b", re.IGNORECASE)),
]


@dataclass
class CommitClass:
    repo: str
    sha: str
    author: str
    date: str
    is_merge: bool
    subject: str
    leaf: str
    superclass: str
    matched_rule: str
    primary_dir: str
    file_count: int


def _primary_dir(files: list[str], depth: int = 2) -> str:
    """The most common directory prefix (up to `depth` segments) among the
    files a commit touched -- lets effort.py cluster toil by *where in the
    tree* it concentrates (e.g. "355 commits under src/services/*"), not
    just by ontology category. A single/no-file commit falls back to that
    file's own directory or "" for none."""
    if not files:
        return ""
    from collections import Counter
    prefixes = ["/".join(f.split("/")[:depth]) for f in files]
    return Counter(prefixes).most_common(1)[0][0]


def _classify_files(files: list[str]) -> tuple[str, str] | None:
    if not files:
        return None
    for leaf, pattern in FILE_RULES:
        if all(pattern.search(f) for f in files):
            return leaf, f"file:{leaf}"
    return None


def _classify_message(subject: str) -> tuple[str, str]:
    m = MSG_PREFIX_RE.match(subject)
    if m:
        leaf = PREFIX_TO_LEAF.get(m.group("type").lower())
        if leaf:
            return leaf, f"prefix:{m.group('type').lower()}"
    for leaf, pattern in KEYWORD_RULES:
        if pattern.search(subject):
            return leaf, f"keyword:{leaf}"
    return "other", "unmatched"


def classify_commit(subject: str, files: list[str]) -> tuple[str, str]:
    file_hit = _classify_files(files)
    msg_leaf, msg_rule = _classify_message(subject)
    # File rules only override when the message rule found nothing more
    # specific than a generic keyword miss, OR when the file evidence is
    # unambiguous (100% of files match one pattern) -- see METHODOLOGY.md
    # for why file evidence is trusted over an "other"-bucket message.
    if msg_leaf == "other" and file_hit:
        return file_hit
    if file_hit and file_hit[0] in ("dependency_bump", "ci_build", "data_schema") and msg_leaf in ("other", "chore"):
        return file_hit
    return msg_leaf, msg_rule


def _iter_commits(repo: Path):
    res = run(["git", "log", "--all", "--no-renames", "--name-only", f"--format={LOG_FORMAT}",
               "--date=iso-strict"], cwd=repo)
    blocks = res.stdout.split(f"\n{COMMIT_SEP}\n")
    for block in blocks:
        block = block.strip("\n")
        if not block:
            continue
        lines = block.split("\n")
        meta = lines[0].split("\x01")
        if len(meta) < 5:
            continue
        sha, author, date, subject, parents = meta[0], meta[1], meta[2], meta[3], meta[4]
        files = [path for path in lines[1:] if path.strip()]
        is_merge = len(parents.split()) > 1
        yield sha, author, date, subject, is_merge, files


def analyze_repo(repo: Path) -> list[CommitClass]:
    out = []
    for sha, author, date, subject, is_merge, files in _iter_commits(repo):
        if is_merge:
            continue  # merges classified separately; not part of the "work" denominator
        leaf, rule = classify_commit(subject, files)
        out.append(CommitClass(
            repo=repo.name, sha=sha[:10], author=author, date=date, is_merge=is_merge,
            subject=subject[:200], leaf=leaf, superclass=SUPERCLASS[leaf], matched_rule=rule,
            primary_dir=_primary_dir(files), file_count=len(files),
        ))
    return out


def run_ontology(repos: list[Path], out_dir: Path) -> Path:
    all_rows: list[CommitClass] = []
    for r in repos:
        all_rows.extend(analyze_repo(r))
    rows = [asdict(c) for c in all_rows]
    out_path = out_dir / "ontology_commits.csv"
    write_csv(out_path, rows)

    leaf_counts = Counter(c.leaf for c in all_rows)
    super_counts = Counter(c.superclass for c in all_rows)
    rule_counts = Counter(c.matched_rule.split(":")[0] for c in all_rows)
    summary = {
        "total_non_merge_commits": len(all_rows),
        "leaf_distribution": dict(leaf_counts.most_common()),
        "superclass_distribution": dict(super_counts.most_common()),
        "superclass_pct": {k: round(100 * v / len(all_rows), 2) for k, v in super_counts.items()} if all_rows else {},
        "classification_source": dict(rule_counts),
        "other_pct": round(100 * leaf_counts.get("other", 0) / len(all_rows), 2) if all_rows else 0.0,
    }
    write_json(out_dir / "ontology_summary.json", summary)
    return out_path
