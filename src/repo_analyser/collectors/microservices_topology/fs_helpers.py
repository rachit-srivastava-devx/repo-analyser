"""Shared filesystem/YAML helpers, reimplemented locally rather than
imported from repo_type.py: these are that module's own private helpers
(leading underscore), and this codebase's convention is to duplicate a
small helper like this rather than promote it to a shared module before
a third caller actually needs it (repo_type.SERVICE_MESH_CRD_KINDS is the
different, legitimate case: a *public* module-level constant, imported
directly where needed rather than duplicated here -- see service_mesh.py)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from ...core.lang import EXCLUDE_DIR_PARTS


def _read_yaml_docs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        docs = list(yaml.safe_load_all(path.read_text()))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return []
    return [d for d in docs if isinstance(d, dict)]


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _tracked_files(repo: Path) -> list[Path]:
    return [p for p in repo.rglob("*")
            if p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.relative_to(repo).parts)]


def _collect_yaml_tree(repo: Path) -> tuple[list[dict], str]:
    """One tree walk shared by every k8s-manifest-shaped signal that reads
    it (service mesh, network policy, canary, and the manifest-presence
    gate in analyze.py) rather than a separate walk per signal -- this
    repo can be a 50k-file monorepo (AGENTS.md Sec 3's "Huge" rung).
    Returns (every parsed YAML dict document found in any `.yaml`/`.yml`
    file, the concatenated raw text of every such file -- for the
    sidecar-annotation grep, which is a plain substring match per the
    brief's own "grep any .yaml/.yml file" wording rather than a
    recursive dict-value search)."""
    docs: list[dict] = []
    texts: list[str] = []
    for p in _tracked_files(repo):
        if p.suffix in (".yml", ".yaml"):
            text = _read_text(p)
            if text:
                texts.append(text)
            docs.extend(_read_yaml_docs(p))
    return docs, "\n".join(texts)
