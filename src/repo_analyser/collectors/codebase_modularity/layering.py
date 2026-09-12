"""Signal 3: layering/boundary enforcement -- static config-file presence
detection only, no external tool invocation, same "static config
presence/shape only" precedent as monorepo_tooling (see its `__init__.py`
docstring). Checked at repo root only, regardless of detected repo
language (a JS/TS repo could theoretically have a leftover import-linter
config from a migration, etc. -- presence detection shouldn't assume):

- **dependency-cruiser** (JS/TS): any of `.dependency-cruiser.{js,cjs,
  json,yml,yaml}`, or a `"dependency-cruiser"`/`"depcruise"` top-level key
  in `package.json`.
- **import-linter** (Python): a `.importlinter` file, a `[tool.
  importlinter]` table in `pyproject.toml` (regex presence check, no TOML
  parser -- same call as monorepo_tooling/pants_signals.py and
  tooling_drift/lint_configs.py's own `_has_toml_table`, reimplemented
  locally per collector rather than cross-imported, AGENTS.md §4), or an
  `[importlinter]` section in `setup.cfg` (via stdlib `configparser`,
  since setup.cfg is genuinely INI format, not TOML).
- **go-arch-lint** (Go): `.go-arch-lint.yml`/`.yaml`.

**Explicit scope exclusion**: `cargo-modules` (Rust) is not checked. It's
a CLI query tool invoked ad hoc (`cargo modules generate ...`), not a
persistent config file living in the repo -- there is nothing to detect
via file presence, unlike the other three. Stated here rather than
silently omitted."""
from __future__ import annotations

import json
import re
from configparser import Error as ConfigParserError
from configparser import RawConfigParser
from dataclasses import dataclass
from pathlib import Path

from .patterns import SAMPLE_CAP, join_sample

DEPENDENCY_CRUISER_CONFIG_NAMES = (
    ".dependency-cruiser.js", ".dependency-cruiser.cjs",
    ".dependency-cruiser.json", ".dependency-cruiser.yml", ".dependency-cruiser.yaml",
)
GO_ARCH_LINT_CONFIG_NAMES = (".go-arch-lint.yml", ".go-arch-lint.yaml")
IMPORT_LINTER_CONFIG_NAME = ".importlinter"

_IMPORTLINTER_PYPROJECT_RE = re.compile(r"^\[tool\.importlinter\]", re.MULTILINE)


@dataclass
class LayeringFindings:
    layering_tool_detected: str
    layering_config_path: str


def _dependency_cruiser_hits(repo: Path) -> list[Path]:
    hits = [repo / n for n in DEPENDENCY_CRUISER_CONFIG_NAMES if (repo / n).is_file()]
    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(errors="ignore"))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and ("dependency-cruiser" in data or "depcruise" in data):
            hits.append(pkg)
    return hits


def _import_linter_hits(repo: Path) -> list[Path]:
    hits = []
    dot_file = repo / IMPORT_LINTER_CONFIG_NAME
    if dot_file.is_file():
        hits.append(dot_file)

    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(errors="ignore")
        except OSError:
            text = ""
        if _IMPORTLINTER_PYPROJECT_RE.search(text):
            hits.append(pyproject)

    setup_cfg = repo / "setup.cfg"
    if setup_cfg.is_file():
        parser = RawConfigParser()
        try:
            parser.read(setup_cfg)
        except ConfigParserError:
            pass
        else:
            if parser.has_section("importlinter"):
                hits.append(setup_cfg)
    return hits


def _go_arch_lint_hits(repo: Path) -> list[Path]:
    return [repo / n for n in GO_ARCH_LINT_CONFIG_NAMES if (repo / n).is_file()]


def find_layering_findings(repo: Path) -> LayeringFindings:
    tool_hits: dict[str, list[Path]] = {
        "dependency-cruiser": _dependency_cruiser_hits(repo),
        "import-linter": _import_linter_hits(repo),
        "go-arch-lint": _go_arch_lint_hits(repo),
    }
    tools = [name for name, paths in tool_hits.items() if paths]
    all_paths = sorted(str(p.relative_to(repo)) for paths in tool_hits.values() for p in paths)
    return LayeringFindings(
        layering_tool_detected=";".join(tools),
        layering_config_path=join_sample(all_paths, SAMPLE_CAP),
    )
