"""Content-purpose detectors: qa_testing_infrastructure, ml_data_science,
rag_vector_store, ai_knowledge_base, agent_skills. See content_dev_docs.py
for the first four and content_platform.py / content_registry.py for the
remaining seven plus the dict wiring all sixteen together.
"""
from __future__ import annotations

import re
from pathlib import Path

from .constants import ML_DEP_NAMES, RAG_VECTOR_STORE_NAMES
from .fileio import read_json, tracked_files


def content_qa_testing_infrastructure(repo: Path) -> str | None:
    pkg = read_json(repo / "package.json")
    entry = str(pkg.get("main", "")) + str(pkg.get("exports", ""))
    has_test_preset = any((repo / name).exists() for name in
                          ("playwright.config.ts", "playwright.config.js", "cypress.config.ts"))
    if has_test_preset and re.search(r"fixture|preset|helper", entry, re.IGNORECASE):
        return "test-helper package.json entry point + Playwright/Cypress preset config"
    return None


def content_ml_data_science(repo: Path) -> str | None:
    notebooks = [p for p in tracked_files(repo) if p.suffix == ".ipynb"]
    if notebooks:
        return f"{len(notebooks)} .ipynb notebooks"
    if (repo / "dvc.yaml").is_file() or any((repo).glob("*.dvc")):
        return "dvc.yaml/.dvc"
    for req_name in ("requirements.txt", "pyproject.toml"):
        req = repo / req_name
        if req.is_file() and ML_DEP_NAMES.search(req.read_text(errors="replace")):
            return f"{req_name} names torch/tensorflow/scikit-learn/pandas"
    return None


def content_rag_vector_store(repo: Path) -> str | None:
    for name in ("docker-compose.yml", "docker-compose.yaml", "requirements.txt", "package.json"):
        f = repo / name
        if f.is_file() and RAG_VECTOR_STORE_NAMES.search(f.read_text(errors="replace")):
            return f"{name} references a vector-store (qdrant/weaviate/milvus/chromadb/pgvector)"
    return None


def content_ai_knowledge_base(repo: Path) -> str | None:
    files = tracked_files(repo)
    if not files:
        return None
    md_files = [p for p in files if p.suffix in (".md", ".mdx")]
    if len(md_files) / len(files) < 0.8:
        return None
    for p in md_files[:20]:
        text = p.read_text(errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1 and re.search(r"^(tags|priority|last_verified):", text[3:end], re.MULTILINE):
                return f"{p.name} has structured frontmatter (tags/priority/last_verified)"
    return None


def content_agent_skills(repo: Path) -> str | None:
    if any(p.name == "SKILL.md" for p in tracked_files(repo)):
        return "SKILL.md file(s)"
    if (repo / ".claude" / "skills").is_dir():
        return ".claude/skills/"
    if any(p.name == "mcp.json" for p in tracked_files(repo)):
        return "mcp.json"
    return None
