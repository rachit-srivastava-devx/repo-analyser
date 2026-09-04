"""Language detection shared by depgraph.py, testquality.py, and
duplication.py, so "what language is this repo" is answered once, the same
way, everywhere -- rather than each module guessing independently and
possibly disagreeing.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

EXT_TO_LANG = {
    ".ts": "javascript", ".tsx": "javascript", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python",
    ".go": "go",
    ".java": "java", ".kt": "java",
    ".rb": "ruby",
    ".rs": "rust",
}
EXCLUDE_DIR_PARTS = {"node_modules", "dist", "build", ".git", "coverage", ".next", ".turbo",
                     "venv", ".venv", "__pycache__", "vendor", "target"}

# Which languages depgraph.py / testquality.py actually implement support
# for -- kept explicit so an unsupported language reports "not supported"
# rather than silently producing an empty/wrong result.
DEPGRAPH_SUPPORTED = {"javascript", "python", "go"}
TESTQUALITY_SUPPORTED = {"javascript", "python", "go"}

# jscpd's --format language names (https://github.com/kucherenko/jscpd) --
# not always the same string as our internal EXT_TO_LANG values.
JSCPD_FORMAT = {
    "javascript": "javascript,typescript,jsx,tsx",
    "python": "python",
    "go": "go",
    "java": "java",
    "ruby": "ruby",
    "rust": "rust",
}


def detect_repo_language(repo: Path) -> str:
    """Dominant language by file count. Returns "unknown" if nothing
    recognized is found (e.g. a pure-Terraform or pure-docs repo)."""
    counts: Counter[str] = Counter()
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        lang = EXT_TO_LANG.get(p.suffix)
        if lang:
            counts[lang] += 1
    if not counts:
        return "unknown"
    return counts.most_common(1)[0][0]


def detect_portfolio_languages(repos: list[Path]) -> set[str]:
    return {detect_repo_language(r) for r in repos} - {"unknown"}
