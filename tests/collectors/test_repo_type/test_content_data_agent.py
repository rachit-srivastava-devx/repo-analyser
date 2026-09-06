from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestContentTypeQaTestingInfrastructure:
    def test_playwright_preset_with_helper_entry_point(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "playwright.config.ts").write_text("export default {};\n")
        (repo / "package.json").write_text(json.dumps({"name": "x", "main": "./test-helper.js"}))
        assert "qa_testing_infrastructure" in analyze_repo(repo, [repo]).content_types

    def test_preset_config_without_helper_entry_point_does_not_match(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "cypress.config.ts").write_text("export default {};\n")
        (repo / "package.json").write_text(json.dumps({"name": "x", "main": "./index.js"}))
        assert "qa_testing_infrastructure" not in analyze_repo(repo, [repo]).content_types


class TestContentTypeMlDataScience:
    def test_ipynb_notebooks(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text("{}")
        assert "ml_data_science" in analyze_repo(repo, [repo]).content_types

    def test_requirements_names_torch(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "requirements.txt").write_text("torch==2.0.0\nnumpy==1.0\n")
        assert "ml_data_science" in analyze_repo(repo, [repo]).content_types


class TestContentTypeRagVectorStore:
    def test_docker_compose_references_qdrant(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "docker-compose.yml").write_text("services:\n  qdrant:\n    image: qdrant/qdrant\n")
        assert "rag_vector_store" in analyze_repo(repo, [repo]).content_types


class TestContentTypeAiKnowledgeBase:
    def test_almost_all_markdown_with_structured_frontmatter(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        for i in range(5):
            (repo / f"kb{i}.md").write_text(
                "---\ntags: [a, b]\npriority: high\nlast_verified: 2026-01-01\n---\n\ncontent\n"
            )
        assert "ai_knowledge_base" in analyze_repo(repo, [repo]).content_types

    def test_plain_markdown_without_frontmatter_does_not_match(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        for i in range(5):
            (repo / f"doc{i}.md").write_text("# just a heading\n")
        assert "ai_knowledge_base" not in analyze_repo(repo, [repo]).content_types


class TestContentTypeAgentSkills:
    def test_skill_md_file(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "SKILL.md").write_text("# Skill\n")
        assert "agent_skills" in analyze_repo(repo, [repo]).content_types

    def test_claude_skills_dir(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / ".claude" / "skills").mkdir(parents=True)
        assert "agent_skills" in analyze_repo(repo, [repo]).content_types
