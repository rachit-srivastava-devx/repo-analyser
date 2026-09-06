"""The first three primary-axis checks in detecting-repo-type.md's listed
order: meta-repo, monorepo, microservices. See primary_type.py for the
remaining two (polyrepo, single-repo default) and the function that runs
all five in priority order.
"""
from __future__ import annotations

import re
from pathlib import Path

from .constants import MANIFEST_ROOT_FILES, MONOREPO_BUILD_MARKERS, MONOREPO_JS_MARKERS, SERVICE_MESH_CRD_KINDS
from .fileio import immediate_subdirs, read_yaml_docs, tracked_files


def detect_meta_repo(repo: Path) -> str | None:
    gitmodules = repo / ".gitmodules"
    if gitmodules.is_file():
        entries = len(re.findall(r"^\[submodule ", gitmodules.read_text(errors="replace"), re.MULTILINE))
        other_source = sum(1 for p in tracked_files(repo) if p.suffix in
                            {".py", ".js", ".ts", ".go", ".rs", ".java"})
        if entries >= 3 and other_source < entries:
            return f".gitmodules ({entries} submodules, {other_source} other source files)"
    if (repo / "manifest.xml").is_file() or (repo / ".repo").is_dir():
        return "manifest.xml/.repo (AOSP repo tool)"
    if (repo / "west.yml").is_file():
        return "west.yml (Zephyr)"
    return None


def detect_monorepo(repo: Path) -> tuple[str | None, str]:
    for marker in MONOREPO_JS_MARKERS:
        if (repo / marker).is_file():
            return marker, "monorepo (JS/TS ecosystem)"
    for marker in MONOREPO_BUILD_MARKERS:
        if (repo / marker).is_file():
            return marker, "monorepo (Bazel/Buck2/Pants)"
    # Unmanaged monorepo: 2+ immediate subdirectories each with their own
    # manifest, no shared workspace marker at root. A real, if fuzzy, signal
    # -- detecting-repo-type.md's own caveat ("verify no separate CI/build
    # per folder before assuming polyrepo") is exactly why this is reported
    # as a *note*, not asserted with false confidence.
    sibling_manifests = [d.name for d in immediate_subdirs(repo)
                          if any((d / m).is_file() for m in MANIFEST_ROOT_FILES)]
    if len(sibling_manifests) >= 2:
        return (";".join(sorted(sibling_manifests)),
                "monorepo, unmanaged (multiple sibling manifests, no shared workspace file)")
    return None, ""


def detect_microservices(repo: Path) -> tuple[str | None, str]:
    dockerfiles = [p for p in tracked_files(repo) if p.name == "Dockerfile"]
    if len(dockerfiles) >= 2:
        return f"{len(dockerfiles)} Dockerfiles", "microservices architecture"
    for compose_name in ("docker-compose.yml", "docker-compose.yaml"):
        docs = read_yaml_docs(repo / compose_name)
        for doc in docs:
            services = doc.get("services")
            if isinstance(services, dict) and len(services) >= 2:
                return f"{compose_name} ({len(services)} services)", "microservices architecture"
    for p in tracked_files(repo):
        if p.suffix in (".yml", ".yaml"):
            for doc in read_yaml_docs(p):
                kind = doc.get("kind")
                if kind in SERVICE_MESH_CRD_KINDS:
                    return f"{p.name}: kind={kind}", "microservices on a service mesh"
    return None, ""
