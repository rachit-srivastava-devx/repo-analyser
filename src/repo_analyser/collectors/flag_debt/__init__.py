"""Feature-flag debt: which feature-flag SDKs a repo uses (if any), which
flags its own code references via a known in-house is_enabled(...)-style
gate, which flags are defined (a root config file or a source dict
literal), and where those two sets disagree -- an orphaned definition
(defined, never referenced -- dead config) or an undefined reference
(referenced, no local definition found). The latter is a *signal*, not
certainty: an SDK-managed remote flag has no local definition by design, so
a nonzero count here is expected and normal, not necessarily a bug.

See docs/checklist-by-repo-type/single-repo.md's "Configuration &
feature-flag debt" row for the criterion this answers.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import FlagDebtResult
from .runner import run_flag_debt

__all__ = ["FlagDebtResult", "analyze_repo", "run_flag_debt"]
