"""Per-ADR tallying: walks the discovered ADR files once, combining the
section/reversibility text signals (adr_sections.py) with the status +
post-acceptance-modification git signal (adr_status_git.py) into the six
aggregate counts analyze.py needs. Split out of analyze.py purely to keep
that file under the package's ~80-line convention -- this is orchestration,
not a new signal of its own."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adr_sections import has_standard_sections, is_reversibility_tagged
from .adr_status_git import detect_status, modified_after_acceptance
from .text_io import read_text_safe


@dataclass
class AdrTally:
    malformed: int = 0
    with_standard_sections: int = 0
    status_accepted: int = 0
    status_unknown: int = 0
    modified_after_acceptance: int = 0
    acceptance_history_unknown: int = 0
    reversibility_tagged: int = 0


def tally_adrs(repo: Path, adr_files: list[Path], adr_rel_paths: list[str]) -> AdrTally:
    t = AdrTally()
    for p, rel in zip(adr_files, adr_rel_paths, strict=True):
        text, err = read_text_safe(p)
        if err or text is None:
            t.malformed += 1
            continue
        if has_standard_sections(text):
            t.with_standard_sections += 1
        if is_reversibility_tagged(text):
            t.reversibility_tagged += 1
        status = detect_status(text)
        if status == "accepted":
            t.status_accepted += 1
            outcome = modified_after_acceptance(repo, rel)
            if outcome == "yes":
                t.modified_after_acceptance += 1
            elif outcome == "unknown":
                t.acceptance_history_unknown += 1
        elif status == "":
            t.status_unknown += 1
    return t
