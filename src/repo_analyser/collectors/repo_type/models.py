from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepoTypeResult:
    repo: str
    primary_type: str
    content_types: str
    signals_matched: str
    detection_notes: str
