"""Content-purpose detectors: library_package, infra_gitops, docs_repo,
developer_tools. See content_data_agent.py and content_platform.py for the
next nine, and content_registry.py for the final three plus the dict that
wires all sixteen together.
"""
from __future__ import annotations

from pathlib import Path

from .fileio import read_json, read_toml_has_table, tracked_files


def content_library_package(repo: Path) -> str | None:
    pkg = read_json(repo / "package.json")
    if pkg and any(k in pkg for k in ("main", "exports", "types")) and not (repo / "Dockerfile").is_file():
        return "package.json main/exports/types, no Dockerfile"
    if read_toml_has_table(repo / "pyproject.toml", "build-system") or (repo / "setup.py").is_file():
        return "pyproject.toml [build-system] or setup.py"
    return None


def content_infra_gitops(repo: Path) -> str | None:
    tf_files = [p for p in tracked_files(repo) if p.suffix in (".tf", ".json") and p.suffix == ".tf"]
    if tf_files:
        return f"{len(tf_files)} .tf files"
    if (repo / "Chart.yaml").is_file():
        return "Chart.yaml (Helm)"
    if any(p.name in ("kustomization.yaml", "kustomization.yml") for p in tracked_files(repo)):
        return "kustomization.yaml"
    return None


def content_docs_repo(repo: Path) -> str | None:
    files = tracked_files(repo)
    if not files:
        return None
    doc_files = [p for p in files if p.suffix in (".md", ".mdx", ".rst")]
    if len(doc_files) / len(files) > 0.5:
        return f"{len(doc_files)}/{len(files)} files are .md/.mdx/.rst"
    for marker in ("docusaurus.config.js", "mkdocs.yml", "conf.py"):
        if (repo / marker).is_file():
            return marker
    if (repo / ".vitepress").is_dir():
        return ".vitepress"
    return None


def content_developer_tools(repo: Path) -> str | None:
    pkg = read_json(repo / "package.json")
    if "bin" in pkg:
        return "package.json bin field"
    if "contributes" in pkg and "engines" in pkg and "vscode" in pkg.get("engines", {}):
        return "VS Code extension (contributes + engines.vscode)"
    if (repo / "cmd").is_dir():
        return "cmd/ directory (Go)"
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file() and "[project.scripts]" in pyproject.read_text(errors="replace"):
        return "pyproject.toml [project.scripts]"
    return None
