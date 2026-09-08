"""Architecture & Design Documentation discipline detection: does a
top-level architecture doc exist and stay fresh relative to the repo's own
activity; is there an ADR directory with a real per-decision
context/decision/consequences shape, an accepted-status marker that isn't
silently edited after the fact, and an explicit reversibility tag; and is
there a runbook/operational doc (dedicated file or a README section) with
at least the shape of deploy/rollback/on-call/known-failure-mode content.
See docs/checklist-by-repo-type/single-repo.md's "Architecture & Design
Documentation" section for the 7 criteria this collector answers a static-
inspection-reachable subset of, and docs/METHODOLOGY.md for the exact
detection method and known limitations.

NOT to be confused with the `doc_quality` collector (merged the same
night): doc_quality answers doc-comment coverage (interrogate/JSDoc) and
changelog discipline -- a completely different checklist item. This
package answers none of that; the two never overlap in scope or column
names.

Three independent signal groups, checked and reported independently --
never averaged into one score (docs/ARCHITECTURE.md's "two tools measuring
the same thing stay two separate outputs" rule, applied here to "three
document kinds measuring different things"):

  1. has_hld / hld_docs_found / hld_untracked_count /
     hld_days_since_doc_touched / hld_days_since_repo_last_commit /
     repo_has_commits -- presence of any of five conventional architecture-
     doc paths (all found are reported, not just the first), plus a
     staleness *signal*: two independent "days since" numbers (both
     relative to analysis time, same convention as inventory's own
     days_since_last_commit), left for the reader to compare rather than
     banded into a verdict. An HLD doc that exists but has no git history
     (untracked/uncommitted) still counts as present -- this collector's
     filesystem-first existence check matches api_contract's/
     migration_hygiene's own precedent -- but contributes no freshness
     signal, since freshness is inherently a git-history question an
     untracked file has no answer to (hld_days_since_doc_touched stays
     None for an untracked-only set, distinctly from "very fresh").
     repo_has_commits is False, and both freshness fields are None, for a
     genuinely zero-commit repo -- never a fabricated "0 days stale".
  2. has_adr_dir / adr_dirs_found / adr_file_count / adr_files_sample /
     adr_malformed_count / adr_with_standard_sections_count --
     docs/adr/, docs/decisions/, or adr/ (this repo's own convention, or
     generic MADR-style NNNN-title.md), non-recursive per directory. A
     file that can't be decoded as UTF-8 is counted (adr_malformed_count)
     but excluded from every content-based signal below it, rather than
     crashing the whole collector run.
  3. adr_status_accepted_count / adr_status_unknown_count /
     adr_modified_after_acceptance_count /
     adr_acceptance_history_unknown_count -- of the ADRs whose *current*
     content shows an accepted-status marker, how many were touched by a
     commit *after* the commit that first introduced that marker text.
     This can only report the fact of post-acceptance modification, never
     what changed -- a typo fix and a real status reversal look identical
     to this check, stated plainly rather than editorialized.
     adr_status_unknown_count is an ADR with no recognizable status marker
     at all, reported as such rather than guessed at.
  4. adr_reversibility_tagged_count -- of adr_file_count, how many ADRs
     carry an explicit one-way-door/two-way-door/reversible/irreversible
     tag anywhere in their text (case-insensitive, word-boundary).
  5. has_runbook / runbook_docs_found / runbook_keyword_categories_found /
     runbook_keyword_category_count -- a dedicated file (RUNBOOK.md,
     docs/runbook.md, docs/operations.md, docs/on-call.md) or a Runbook/
     Rollback/On-call-shaped README section, plus a lightweight keyword-
     presence signal (deploy/rollback/on-call/known-failure-mode) across
     whatever runbook-ish text was found -- not semantic understanding of
     whether the procedures are actually correct or current.

skip_reason is populated only when none of the three top-level signals
(has_hld, has_adr_dir, has_runbook) found anything at all -- the "empty
repo, no docs at all" edge case named explicitly in this collector's build
task. It says nothing about any one signal group on its own; a repo with
only a runbook and no HLD/ADRs has skip_reason="" and a real has_hld=False,
matching api_contract's own precedent of tying skip_reason to the
headline absence case rather than every possible partial-miss.

Deliberate v1 scope, stated honestly (see docs/METHODOLOGY.md's new
entry): this collector answers only the 4 of 7 checklist criteria
reachable from pure static file/git inspection. LLD completeness,
design-vs-implementation drift, and public interface documentation all
require either deep semantic understanding of what the code *should* do,
or executing the target's own toolchain against two points in time --
both explicitly out of scope here, named rather than silently dropped.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import DesignDocsResult
from .runner import run_design_docs

__all__ = ["DesignDocsResult", "analyze_repo", "run_design_docs"]
