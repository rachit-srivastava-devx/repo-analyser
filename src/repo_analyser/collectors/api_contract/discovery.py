"""Finds candidate API/schema spec files across all three kinds. Walks the
filesystem (like depgraph.py/duplication.py), not `git ls-files` -- a
gitignored or untracked-but-present spec file is still a real, checkable-
out file a developer or CI could read, so it counts here. Documented,
deliberate choice: every other filesystem-walking collector in this repo
already treats EXCLUDE_DIR_PARTS as the only exclusion rule rather than
consulting .gitignore, and this module follows the same convention rather
than inventing a second policy.

Precedence on simultaneous matches (openapi > graphql > protobuf, the
schema_kind enum's own listed order) is applied by analyze.py, not here --
this module reports everything found, unfiltered.
"""
from __future__ import annotations

from pathlib import Path

from ...core.lang import EXCLUDE_DIR_PARTS
from .openapi_discovery import find_openapi_files
from .patterns import GRAPHQL_SUFFIXES, PROTO_SUFFIX

__all__ = ["find_openapi_files", "find_graphql_and_protobuf_files"]


def find_graphql_and_protobuf_files(repo: Path) -> tuple[list[Path], list[Path]]:
    """Single bounded tree walk for both kinds so a large repo (the
    "monorepo with 50k files" edge case) is walked once, not twice."""
    graphql: list[Path] = []
    protobuf: list[Path] = []
    for p in repo.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        if p.suffix in GRAPHQL_SUFFIXES:
            graphql.append(p)
        elif p.suffix == PROTO_SUFFIX:
            protobuf.append(p)
    return graphql, protobuf
