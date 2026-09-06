"""Generic dependency-version drift comparison, format-agnostic: given the
parsed {name: version} dict for each of >=2 manifests of a SINGLE
ecosystem, finds which dependency names disagree on version. Consumed by
dependency_version_check.py, which runs this once per ecosystem
(package.json, go.mod) and merges the results into one row.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import MIN_MANIFESTS_TO_COMPARE


def dependency_drift(parsed_by_manifest: dict[Path, dict[str, str]]) -> tuple[int, int, list[str]]:
    """`parsed_by_manifest`: manifest path -> {dep_name: version}, for
    >=2 manifests of a SINGLE ecosystem (caller's responsibility -- this
    never mixes package.json and go.mod names together).

    Returns (packages_compared, packages_with_drift, drift_detail_parts).
    `packages_compared` counts only dependency names that appear in AT
    LEAST TWO of the given manifests -- a name declared in just one
    manifest has nothing to compare against, so it's not "compared" at
    all, matching "the SAME dependency name... across two or more of
    those manifests" in this package's own brief. `packages_with_drift`
    is the subset of those with more than one distinct version string
    pinned across the manifests that declare it."""
    name_to_versions: dict[str, set[str]] = defaultdict(set)
    name_occurrences: dict[str, int] = defaultdict(int)
    for deps in parsed_by_manifest.values():
        for name, version in deps.items():
            name_to_versions[name].add(version)
            name_occurrences[name] += 1
    compared = sorted(name for name, count in name_occurrences.items() if count >= MIN_MANIFESTS_TO_COMPARE)
    detail: list[str] = []
    drifted = 0
    for name in compared:
        versions = name_to_versions[name]
        if len(versions) > 1:
            drifted += 1
            detail.extend(f"{name}@{v}" for v in sorted(versions))
    return len(compared), drifted, detail
