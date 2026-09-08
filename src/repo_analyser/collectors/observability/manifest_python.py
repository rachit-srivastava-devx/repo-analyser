"""requirements.txt + pyproject.toml reading -- the Python half of
dependency-manifest parsing.

No TOML-parsing dependency exists in this project, and its own floor is
Python 3.10 (pyproject.toml's `requires-python`), where stdlib `tomllib`
does not exist yet -- so pyproject.toml dependency names are extracted
with the same "text pattern, not full grammar" approach performance.py/
e2e_quality.py already use for CI YAML step text, not a real TOML parse.
Handles PEP 621's top-level `dependencies = [...]` array and a Poetry-style
`[tool.poetry(.group.x).dependencies]` table. Does NOT handle PEP 621
`[project.optional-dependencies]` extras groups, or `dynamic =
["dependencies"]` metadata deferred to another file -- both real, out of
scope for a presence-only check against a small known-name list.
"""
from __future__ import annotations

import re
from pathlib import Path

_PEP621_DEPS_RE = re.compile(r"dependencies\s*=\s*\[(.*?)\]", re.DOTALL)
_QUOTED_ENTRY_RE = re.compile(r"""["']([^"']+)["']""")


def normalize_pypi_name(name: str) -> str:
    """PEP 503 canonicalization: lowercase, and runs of "-_." collapsed to
    a single "-" -- so "prometheus_client" (the name most repos actually
    write, matching the import name) and "prometheus-client" (PyPI's own
    canonical distribution name) compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_requirements_txt(repo: Path) -> set[str]:
    req = repo / "requirements.txt"
    if not req.exists():
        return set()
    names: set[str] = set()
    for raw_line in req.read_text(errors="replace").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            # blank/comment-only lines, and pip options/other-file
            # references (-r other.txt, --index-url, -e git+...) -- not a
            # package name, and not followed here (known limitation).
            continue
        m = re.match(r"[A-Za-z0-9_.\-]+", line)
        if m:
            names.add(normalize_pypi_name(m.group(0)))
    return names


def read_pyproject_toml_deps(repo: Path) -> set[str]:
    pp = repo / "pyproject.toml"
    if not pp.exists():
        return set()
    text = pp.read_text(errors="replace")
    names: set[str] = set()

    m = _PEP621_DEPS_RE.search(text)
    if m:
        for entry in _QUOTED_ENTRY_RE.findall(m.group(1)):
            name_match = re.match(r"[A-Za-z0-9_.\-]+", entry)
            if name_match:
                names.add(normalize_pypi_name(name_match.group(0)))

    in_poetry_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_poetry_deps = "poetry" in stripped and "dependencies" in stripped
            continue
        if in_poetry_deps and "=" in stripped and not stripped.startswith("#"):
            name = stripped.split("=", 1)[0].strip().strip("\"'")
            if name and name.lower() != "python":
                names.add(normalize_pypi_name(name))
    return names
