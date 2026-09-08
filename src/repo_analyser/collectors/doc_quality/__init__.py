"""Doc-comment coverage + changelog discipline (docs/ROADMAP.md, "Checklist-by-repo-type
build-out" -> New collectors -> doc_quality.py).

v1 scope, stated plainly: doc-comment coverage and changelog discipline ONLY.
Doc-freshness-via-content-matching (diffing a doc's last-edit date against
the source it actually describes) is explicitly OUT of v1 -- too speculative
to measure reliably (ROADMAP's own reasoning), not silently dropped.

Two independent signal groups, computed the same way for every repo -- doc-
comment coverage (language-dependent: `doc_comment_python.py` for a real
interrogate measurement, `doc_comment_js.py` for a weaker presence-only
JSDoc signal, `go`/`rust` get an explicit `skip_reason` via `analyze.py`'s
dispatch -- no keyless scriptable tool exists for those yet) and changelog
discipline (`changelog_parse.py` for presence + last-entry-date,
`changelog_staleness.py` for the git-tag comparison -- pure git + filesystem,
no external tool). See each submodule's own docstring for the full signal
writeup; `analyze.py` combines both groups per repo and `runner.py` writes
the portfolio CSV + summary JSON.

Column note: `skip_reason` covers the doc-comment-coverage half only. The
changelog half never has a genuine failure mode of its own -- has_changelog
is always a real True/False, and changelog_stale_vs_latest_tag's own
"unknown" state already names every case where the changelog side can't be
computed -- so there is no separate silent-empty-result risk to flag there.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import DocQualityResult
from .runner import run_doc_quality

__all__ = ["DocQualityResult", "analyze_repo", "run_doc_quality"]
