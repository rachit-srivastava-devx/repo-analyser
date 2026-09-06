from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.microservices_topology.resilience_libs import _resilience_libs_detected


class TestResilienceLibsDetected:
    def test_pybreaker_in_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask==3.0\npybreaker==1.2.0\n")
        assert _resilience_libs_detected(tmp_path) == {"pybreaker"}

    def test_tenacity_in_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["tenacity>=8.0"]\n')
        assert _resilience_libs_detected(tmp_path) == {"tenacity"}

    def test_opossum_in_package_json_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"opossum": "^8.0.0"}}))
        assert _resilience_libs_detected(tmp_path) == {"opossum"}

    def test_cockatiel_in_package_json_dev_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"cockatiel": "^3.1.0"}}))
        assert _resilience_libs_detected(tmp_path) == {"cockatiel"}

    def test_sony_gobreaker_in_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/x\n\nrequire github.com/sony/gobreaker v0.5.0\n")
        assert _resilience_libs_detected(tmp_path) == {"sony/gobreaker"}

    def test_avast_retry_go_in_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/x\n\nrequire github.com/avast/retry-go v3.1.1\n")
        assert _resilience_libs_detected(tmp_path) == {"avast/retry-go"}

    def test_no_manifests_detects_nothing(self, tmp_path: Path) -> None:
        assert _resilience_libs_detected(tmp_path) == set()

    def test_unrelated_dependency_detects_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.31\n")
        assert _resilience_libs_detected(tmp_path) == set()

    def test_malformed_package_json_does_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not valid json,,,")
        assert _resilience_libs_detected(tmp_path) == set()
