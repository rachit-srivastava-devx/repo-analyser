from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestPrimaryTypeMetaRepo:
    def test_gitmodules_heavy_with_little_own_source(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / ".gitmodules").write_text(
            "[submodule \"a\"]\n\tpath = a\n\turl = https://example.com/a\n"
            "[submodule \"b\"]\n\tpath = b\n\turl = https://example.com/b\n"
            "[submodule \"c\"]\n\tpath = c\n\turl = https://example.com/c\n"
        )
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "meta_repo"

    def test_west_yml_zephyr(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "west.yml").write_text("manifest:\n  remotes: []\n")
        assert analyze_repo(repo, [repo]).primary_type == "meta_repo"

    def test_manifest_xml_aosp_repo_tool(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "manifest.xml").write_text("<manifest></manifest>")
        assert analyze_repo(repo, [repo]).primary_type == "meta_repo"

    def test_gitmodules_with_substantial_own_source_is_not_meta_repo(self, tmp_path: Path) -> None:
        # a real app that happens to use ONE submodule shouldn't be
        # misclassified just because .gitmodules exists at all.
        repo = _git_repo(tmp_path / "repo")
        (repo / ".gitmodules").write_text("[submodule \"vendor/lib\"]\n\tpath = vendor/lib\n\turl = https://x\n")
        for i in range(5):
            (repo / f"mod_{i}.py").write_text("x = 1\n")
        assert analyze_repo(repo, [repo]).primary_type == "single_repo"


class TestPrimaryTypeMicroservices:
    def test_multiple_dockerfiles(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "svc-a").mkdir()
        (repo / "svc-a" / "Dockerfile").write_text("FROM scratch\n")
        (repo / "svc-b").mkdir()
        (repo / "svc-b" / "Dockerfile").write_text("FROM scratch\n")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "microservices"

    def test_docker_compose_two_plus_services(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "docker-compose.yml").write_text(
            "services:\n  api:\n    image: api\n  worker:\n    image: worker\n"
        )
        assert analyze_repo(repo, [repo]).primary_type == "microservices"

    def test_single_dockerfile_alone_is_not_microservices(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Dockerfile").write_text("FROM scratch\n")
        assert analyze_repo(repo, [repo]).primary_type == "single_repo"

    def test_istio_virtualservice_crd(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "vs.yaml").write_text("apiVersion: networking.istio.io/v1\nkind: VirtualService\n")
        result = analyze_repo(repo, [repo])
        assert result.primary_type == "microservices"
        assert "service mesh" in result.detection_notes
