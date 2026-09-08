"""Per-repo orchestration: combines HLD, ADR, and runbook detection into one
DesignDocsResult. See package docstring for the full contract and
precedence rules."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .adr_discovery import find_adr_dirs, find_adr_files
from .adr_tally import tally_adrs
from .hld import collect_hld_signal
from .models import SAMPLE_CAP, DesignDocsResult
from .runbook import collect_runbook_signal
from .text_io import join_sample


def _rel(repo: Path, p: Path) -> str:
    try:
        return str(p.relative_to(repo))
    except ValueError:
        return str(p)


def analyze_repo(repo: Path, now: datetime | None = None) -> DesignDocsResult:
    now = now or datetime.now(timezone.utc)

    hld = collect_hld_signal(repo, now)

    adr_dirs = find_adr_dirs(repo)
    adr_files = find_adr_files(repo, adr_dirs)
    adr_rel_paths = [_rel(repo, p) for p in adr_files]
    tally = tally_adrs(repo, adr_files, adr_rel_paths)

    runbook = collect_runbook_signal(repo)

    skip_reason = "" if (hld.has_hld or bool(adr_dirs) or runbook.has_runbook) else (
        "no architecture doc, ADR directory, or runbook found"
    )

    return DesignDocsResult(
        repo=repo.name,
        has_hld=hld.has_hld,
        hld_docs_found=";".join(hld.docs_found),
        hld_untracked_count=hld.untracked_count,
        hld_days_since_doc_touched=hld.days_since_doc_touched,
        hld_days_since_repo_last_commit=hld.days_since_repo_last_commit,
        repo_has_commits=hld.repo_has_commits,
        has_adr_dir=bool(adr_dirs),
        adr_dirs_found=";".join(adr_dirs),
        adr_file_count=len(adr_files),
        adr_files_sample=join_sample(adr_rel_paths, SAMPLE_CAP),
        adr_malformed_count=tally.malformed,
        adr_with_standard_sections_count=tally.with_standard_sections,
        adr_status_accepted_count=tally.status_accepted,
        adr_status_unknown_count=tally.status_unknown,
        adr_modified_after_acceptance_count=tally.modified_after_acceptance,
        adr_acceptance_history_unknown_count=tally.acceptance_history_unknown,
        adr_reversibility_tagged_count=tally.reversibility_tagged,
        has_runbook=runbook.has_runbook,
        runbook_docs_found=";".join(runbook.docs_found),
        runbook_keyword_categories_found=";".join(runbook.keyword_categories),
        runbook_keyword_category_count=len(runbook.keyword_categories),
        skip_reason=skip_reason,
    )
