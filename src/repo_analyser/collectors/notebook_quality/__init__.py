"""ML/data-science notebook hygiene collector.

See docs/checklist-by-repo-type/ml-data-science.md's "Notebook hygiene"
criterion. Split by concern across this package's submodules -- see each
one's own docstring for what it covers; `analyze.py` has the full
three-signal writeup.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import NotebookQualityResult
from .runner import run_notebook_quality

__all__ = ["NotebookQualityResult", "analyze_repo", "run_notebook_quality"]
