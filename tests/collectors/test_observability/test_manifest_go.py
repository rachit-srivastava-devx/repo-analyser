from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.observability.manifest_go import read_go_mod_modules


class TestReadGoModModules:
    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        assert read_go_mod_modules(tmp_path) == set()

    def test_require_block(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module github.com/example/service\n\n"
            "go 1.21\n\n"
            "require (\n"
            "\tgithub.com/prometheus/client_golang v1.17.0\n"
            "\tgo.opentelemetry.io/otel v1.19.0\n"
            ")\n"
        )
        modules = read_go_mod_modules(tmp_path)
        assert "github.com/prometheus/client_golang" in modules
        assert "go.opentelemetry.io/otel" in modules
        # the module's own declaration and the go-version directive must
        # never be mistaken for a dependency.
        assert "github.com/example/service" not in modules
        assert "go" not in modules

    def test_single_line_require_with_indirect_comment(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module github.com/example/service\n\ngo 1.21\n\n"
            "require github.com/rs/zerolog v1.31.0 // indirect\n"
        )
        assert "github.com/rs/zerolog" in read_go_mod_modules(tmp_path)
