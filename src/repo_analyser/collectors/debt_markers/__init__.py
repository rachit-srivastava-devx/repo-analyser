"""Tech-debt backlog size & age: docs/checklist-by-repo-type/single-repo.md's
"Maintainability & Technical Debt" row -- count and average age of TODO/
FIXME/HACK/XXX/BUG markers left in tracked source, watched for silent
growth. Keyless, no external tool: a `git ls-files` walk plus `git blame`,
the ripgrep-TODO-audit half of that row's keyless-tool list (SonarQube
Community Edition is the other; not run here -- no external tool
invocation, matching flag_debt's own "regex/text scanning, not a parser"
scope).

Not a rebuild of flag_debt/ (feature-flag definitions/references, a
different dimension) -- confirmed by grepping the whole collectors/ tree
for TODO/FIXME detection logic before starting; the only pre-existing hits
were incidental literal "TODO" substrings inside api_contract's own
CI-tool-name pattern lists, not a debt-marker detector.

Pipeline, one pass per repo:
  1. `discovery.iter_tracked_files` -- `git ls-files`, so gitignored/
     untracked files are excluded (same discipline as every other
     collector's file-walk).
  2. `markers.find_markers_in_text` -- word-boundary + comment-prefix
     regex scan of each file's text (skipping binary/non-UTF8 content
     entirely, not decoding it lossily -- see discovery.py).
  3. `blame_age.line_author_times` -- one `git blame --line-porcelain`
     call per file *that had a match*, not per match (see blame_age.py's
     docstring for why this matters at scale).
  4. `aggregate.collect` -- rolls the above into count-by-type,
     average/oldest age, and a stale count (age >
     `aggregate.STALE_MARKER_AGE_DAYS`, a named, documented default --
     same "defensible constant, not invented" convention as
     codebase_modularity/module_size.py's 500-LOC/40-file thresholds).
  5. `analyze.analyze_repo` -- precondition checks (skip_reason) plus
     shaping the aggregate into one DebtMarkersResult.

`skip_reason` is populated only for a genuine precondition failure (path
doesn't exist, or isn't a git repo) -- an empty repo or a repo with zero
markers is a real all-zero result, not a skip.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import DebtMarkersResult
from .runner import run_debt_markers

__all__ = ["DebtMarkersResult", "analyze_repo", "run_debt_markers"]
