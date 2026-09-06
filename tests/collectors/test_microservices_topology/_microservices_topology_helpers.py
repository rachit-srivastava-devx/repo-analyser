from __future__ import annotations

from pathlib import Path

import yaml


def _write_compose(repo: Path, services: dict) -> None:
    (repo / "docker-compose.yml").write_text(yaml.safe_dump({"services": services}))
