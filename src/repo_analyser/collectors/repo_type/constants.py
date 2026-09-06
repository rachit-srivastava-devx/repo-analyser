"""Marker files/globs and regexes for both detection axes, per
docs/checklist-by-repo-type/detecting-repo-type.md's signal table -- kept apart
from the detection logic itself so each axis's own module stays under the
package's file-size convention.
"""
from __future__ import annotations

import re

# -- Primary architecture axis: checked in this order, first match wins. --

MONOREPO_JS_MARKERS = ("nx.json", "turbo.json", "pnpm-workspace.yaml", "lerna.json", "rush.json")
MONOREPO_BUILD_MARKERS = ("WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel", "BUCK", "pants.toml")
MANIFEST_ROOT_FILES = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml")
POLYREPO_REGISTRY_MARKERS = ("catalog-info.yaml",)
# Real-world minimum before "org has many similarly-shaped repos" is a
# meaningful signal rather than a coincidence of 2-3 repos looking alike --
# matches detecting-repo-type.md's own literal "10+" wording.
POLYREPO_FLEET_MIN_SIZE = 10

SERVICE_MESH_CRD_KINDS = ("VirtualService", "DestinationRule", "PeerAuthentication")

# -- Content-purpose axis: independent, zero or more can match. --

CONTENT_TYPES_ORDER = (
    "library_package", "infra_gitops", "docs_repo", "developer_tools",
    "qa_testing_infrastructure", "ml_data_science", "rag_vector_store",
    "ai_knowledge_base", "agent_skills", "smart_contract", "mobile_app",
    "design_system", "embedded_firmware", "data_pipeline_etl",
    "browser_extension", "game_engine_or_multiagent",
)

RAG_VECTOR_STORE_NAMES = re.compile(r"qdrant|weaviate|milvus|chromadb|pgvector", re.IGNORECASE)
ML_DEP_NAMES = re.compile(r"^\s*(torch|tensorflow|scikit-learn|sklearn|pandas)\b", re.IGNORECASE | re.MULTILINE)
MULTIAGENT_DEP_NAMES = re.compile(r"langgraph|crewai|pyautogen", re.IGNORECASE)
