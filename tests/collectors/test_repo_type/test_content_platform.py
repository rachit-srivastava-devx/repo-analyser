from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.repo_type import analyze_repo

from ._repo_type_helpers import _git_repo


class TestContentTypeSmartContract:
    def test_sol_files(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Token.sol").write_text("pragma solidity ^0.8.0;\n")
        assert "smart_contract" in analyze_repo(repo, [repo]).content_types

    def test_foundry_toml(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "foundry.toml").write_text("[profile.default]\n")
        assert "smart_contract" in analyze_repo(repo, [repo]).content_types


class TestContentTypeMobileApp:
    def test_info_plist(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "Info.plist").write_text("<plist></plist>")
        assert "mobile_app" in analyze_repo(repo, [repo]).content_types

    def test_android_manifest_and_gradle(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "AndroidManifest.xml").write_text("<manifest></manifest>")
        (repo / "build.gradle").write_text("")
        assert "mobile_app" in analyze_repo(repo, [repo]).content_types

    def test_pubspec_yaml_flutter(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "pubspec.yaml").write_text("name: x\n")
        assert "mobile_app" in analyze_repo(repo, [repo]).content_types


class TestContentTypeDesignSystem:
    def test_storybook_dir(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / ".storybook").mkdir()
        assert "design_system" in analyze_repo(repo, [repo]).content_types


class TestContentTypeEmbeddedFirmware:
    def test_platformio_ini(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "platformio.ini").write_text("[env]\n")
        assert "embedded_firmware" in analyze_repo(repo, [repo]).content_types

    def test_ino_files(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path / "repo")
        (repo / "sketch.ino").write_text("void setup() {}\n")
        assert "embedded_firmware" in analyze_repo(repo, [repo]).content_types
