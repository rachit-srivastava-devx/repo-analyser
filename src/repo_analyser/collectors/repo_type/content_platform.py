"""Content-purpose detectors: smart_contract, mobile_app, design_system,
embedded_firmware. See content_dev_docs.py and content_data_agent.py for the
first nine, and content_registry.py for the final three plus the dict that
wires all sixteen together.
"""
from __future__ import annotations

from pathlib import Path

from .fileio import read_json, tracked_files


def content_smart_contract(repo: Path) -> str | None:
    if any(p.suffix == ".sol" for p in tracked_files(repo)):
        return ".sol files"
    for marker in ("foundry.toml", "hardhat.config.js", "hardhat.config.ts", "truffle-config.js"):
        if (repo / marker).is_file():
            return marker
    return None


def content_mobile_app(repo: Path) -> str | None:
    if any(p.name == "Info.plist" for p in tracked_files(repo)) or \
       any(p.suffix in (".xcodeproj", ".xcworkspace") for p in repo.iterdir() if p.is_dir()):
        return "Info.plist/.xcodeproj/.xcworkspace (iOS)"
    if any(p.name == "AndroidManifest.xml" for p in tracked_files(repo)) and \
       any(p.name in ("build.gradle", "build.gradle.kts") for p in tracked_files(repo)):
        return "AndroidManifest.xml + build.gradle (Android)"
    if (repo / "pubspec.yaml").is_file():
        return "pubspec.yaml (Flutter)"
    pkg = read_json(repo / "package.json")
    if (repo / "app.json").is_file() and "expo" in pkg.get("dependencies", {}):
        return "app.json + Expo config (React Native)"
    return None


def content_design_system(repo: Path) -> str | None:
    return ".storybook/" if (repo / ".storybook").is_dir() else None


def content_embedded_firmware(repo: Path) -> str | None:
    if (repo / "platformio.ini").is_file():
        return "platformio.ini"
    if any(p.suffix == ".ino" for p in tracked_files(repo)):
        return ".ino files"
    makefile = repo / "Makefile"
    if makefile.is_file() and "arm-none-eabi" in makefile.read_text(errors="replace"):
        return "Makefile targeting arm-none-eabi-gcc"
    return None
