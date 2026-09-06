"""CODEOWNERS coverage: whether a repo has one, in GitHub's own precedence
order (.github/CODEOWNERS, then root CODEOWNERS, then docs/CODEOWNERS),
and how much of its tracked file tree its rules actually cover, using the
same last-match-wins semantics as .gitignore. See
docs/checklist-by-repo-type/monorepo.md and polyrepo.md's CODEOWNERS
coverage/accuracy criteria for the source of this shape.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import CodeownersHealthResult
from .runner import run_codeowners_health

__all__ = ["CodeownersHealthResult", "analyze_repo", "run_codeowners_health"]
