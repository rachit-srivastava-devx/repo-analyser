"""Orchestrates one repo's flag-debt analysis: walks its tracked source
files once, collecting SDK imports and flag references in the same pass,
then separately collects flag definitions (root config files plus any
source-level FEATURE_FLAGS/flags dict literal), and diffs the two sets.

undefined_flag_references is a *signal*, not a defect list: an SDK-managed
remote flag (LaunchDarkly, Split.io, Unleash, Flagsmith) is deliberately
defined only in that vendor's dashboard, never in this repo's source -- so
a nonzero count here is expected and normal whenever sdk_detected is
non-empty, not proof of a broken or dead reference.
"""
from __future__ import annotations

from pathlib import Path

from .discovery import iter_source_files, read_text
from .flag_definitions import collect_defined_flags
from .flag_extraction import extract_flag_references
from .models import FlagDebtResult
from .sdk_signatures import find_sdk_import


def analyze_repo(repo: Path) -> FlagDebtResult:
    texts = [read_text(p) for p in iter_source_files(repo)]

    sdks: set[str] = set()
    referenced: set[str] = set()
    for text in texts:
        referenced |= extract_flag_references(text)
        for line in text.splitlines():
            sdk = find_sdk_import(line)
            if sdk:
                sdks.add(sdk)

    raw_defined = collect_defined_flags(repo, texts)
    defined = set(raw_defined)

    return FlagDebtResult(
        repo=str(repo),
        sdk_detected=";".join(sorted(sdks)),
        flags_referenced_count=len(referenced),
        flags_defined_count=len(defined),
        orphaned_flag_definitions=";".join(sorted(defined - referenced)),
        undefined_flag_references=";".join(sorted(referenced - defined)),
        duplicate_definition_count=len(raw_defined) - len(defined),
    )
