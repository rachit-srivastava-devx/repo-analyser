from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.observability.manifest_python import (
    normalize_pypi_name,
    read_pyproject_toml_deps,
    read_requirements_txt,
)


class TestNormalizePypiName:
    def test_underscore_and_hyphen_normalize_the_same(self) -> None:
        assert normalize_pypi_name("prometheus_client") == normalize_pypi_name("prometheus-client")

    def test_lowercased(self) -> None:
        assert normalize_pypi_name("StructLog") == "structlog"


class TestReadRequirementsTxt:
    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        assert read_requirements_txt(tmp_path) == set()

    def test_pinned_and_ranged_versions(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("structlog==23.1.0\nopentelemetry-api>=1.20\n")
        assert read_requirements_txt(tmp_path) == {"structlog", "opentelemetry-api"}

    def test_comments_and_blank_lines_and_options_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text(
            "# a comment\n\n-r other.txt\n--index-url https://example.invalid\nstructlog\n"
        )
        assert read_requirements_txt(tmp_path) == {"structlog"}

    def test_underscore_name_normalizes_same_as_hyphen(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("prometheus_client==0.19.0\n")
        assert read_requirements_txt(tmp_path) == {"prometheus-client"}

    def test_extras_bracket_stripped(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("opentelemetry-api[grpc]==1.20.0\n")
        assert read_requirements_txt(tmp_path) == {"opentelemetry-api"}


class TestReadPyprojectTomlDeps:
    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        assert read_pyproject_toml_deps(tmp_path) == set()

    def test_pep621_dependencies_array(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "example"\ndependencies = [\n    "structlog>=23.1.0",\n    "fastapi",\n]\n'
        )
        assert read_pyproject_toml_deps(tmp_path) == {"structlog", "fastapi"}

    def test_poetry_style_dependencies_table(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.poetry.dependencies]\n"
            'python = "^3.10"\n'
            'structlog = "^23.1.0"\n'
            "[tool.poetry.group.dev.dependencies]\n"
            'pytest = "^7.4"\n'
        )
        names = read_pyproject_toml_deps(tmp_path)
        assert names == {"structlog", "pytest"}
        assert "python" not in names

    def test_unrelated_pyproject_has_no_false_positives(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "example"\ndependencies = ["requests>=2.0"]\n'
        )
        assert read_pyproject_toml_deps(tmp_path) == {"requests"}
