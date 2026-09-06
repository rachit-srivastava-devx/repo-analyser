from __future__ import annotations

from pathlib import Path

from .constants import CONTENT_TYPES_ORDER
from .content_registry import CONTENT_DETECTORS
from .models import RepoTypeResult
from .primary_type import detect_primary_type


def analyze_repo(repo: Path, repos: list[Path]) -> RepoTypeResult:
    primary_type, primary_signal, note = detect_primary_type(repo, repos)
    signals = [primary_signal]
    matched_content: list[str] = []
    for content_type in CONTENT_TYPES_ORDER:
        signal = CONTENT_DETECTORS[content_type](repo)
        if signal:
            matched_content.append(content_type)
            signals.append(f"{content_type}: {signal}")
    return RepoTypeResult(
        repo=repo.name,
        primary_type=primary_type,
        content_types=";".join(matched_content),
        signals_matched=";".join(signals),
        detection_notes=note,
    )
