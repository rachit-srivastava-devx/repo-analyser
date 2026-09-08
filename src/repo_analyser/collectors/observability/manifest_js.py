"""package.json reading -- the JS/TS half of dependency-manifest parsing."""
from __future__ import annotations

import json
from pathlib import Path


def read_package_json(repo: Path) -> dict:
    pj = repo / "package.json"
    if not pj.exists():
        return {}
    try:
        return json.loads(pj.read_text(errors="replace"))
    except json.JSONDecodeError:
        return {}


def js_dependency_names(pkg: dict) -> set[str]:
    deps = pkg.get("dependencies")
    dev_deps = pkg.get("devDependencies")
    names = set(deps) if isinstance(deps, dict) else set()
    names |= set(dev_deps) if isinstance(dev_deps, dict) else set()
    return names
