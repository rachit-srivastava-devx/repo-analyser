"""The last three content-purpose detectors (data_pipeline_etl,
browser_extension, game_engine_or_multiagent), plus CONTENT_DETECTORS: the
dict analyze.py iterates over CONTENT_TYPES_ORDER (constants.py) with, one
entry per content-purpose archetype across all four content_*.py modules.
"""
from __future__ import annotations

from pathlib import Path

from .constants import MULTIAGENT_DEP_NAMES
from .content_data_agent import (
    content_agent_skills,
    content_ai_knowledge_base,
    content_ml_data_science,
    content_qa_testing_infrastructure,
    content_rag_vector_store,
)
from .content_dev_docs import (
    content_developer_tools,
    content_docs_repo,
    content_infra_gitops,
    content_library_package,
)
from .content_platform import (
    content_design_system,
    content_embedded_firmware,
    content_mobile_app,
    content_smart_contract,
)
from .fileio import read_json


def content_data_pipeline_etl(repo: Path) -> str | None:
    if (repo / "dbt_project.yml").is_file():
        return "dbt_project.yml"
    if (repo / "dags").is_dir():
        return "dags/ directory (Airflow)"
    return None


def content_browser_extension(repo: Path) -> str | None:
    manifest = read_json(repo / "manifest.json")
    return f"manifest.json manifest_version={manifest['manifest_version']}" \
        if "manifest_version" in manifest else None


def content_game_engine_or_multiagent(repo: Path) -> str | None:
    if (repo / "Assets").is_dir() and (repo / "ProjectSettings").is_dir():
        return "Assets/ + ProjectSettings/ (Unity)"
    if any(p.suffix == ".uproject" for p in repo.iterdir() if p.is_file()):
        return ".uproject (Unreal)"
    for req_name in ("requirements.txt", "pyproject.toml"):
        req = repo / req_name
        if req.is_file() and MULTIAGENT_DEP_NAMES.search(req.read_text(errors="replace")):
            return f"{req_name} names langgraph/crewai/pyautogen"
    return None


CONTENT_DETECTORS = {
    "library_package": content_library_package,
    "infra_gitops": content_infra_gitops,
    "docs_repo": content_docs_repo,
    "developer_tools": content_developer_tools,
    "qa_testing_infrastructure": content_qa_testing_infrastructure,
    "ml_data_science": content_ml_data_science,
    "rag_vector_store": content_rag_vector_store,
    "ai_knowledge_base": content_ai_knowledge_base,
    "agent_skills": content_agent_skills,
    "smart_contract": content_smart_contract,
    "mobile_app": content_mobile_app,
    "design_system": content_design_system,
    "embedded_firmware": content_embedded_firmware,
    "data_pipeline_etl": content_data_pipeline_etl,
    "browser_extension": content_browser_extension,
    "game_engine_or_multiagent": content_game_engine_or_multiagent,
}
