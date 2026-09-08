"""Merge the three language-specific manifest readers into one flat token
set, and match that set against each signal category's lookup table.
"""
from __future__ import annotations

from pathlib import Path

from .lib_tables import LOGGING_SIGNALS, METRICS_SIGNALS, TRACING_SIGNALS
from .manifest_go import read_go_mod_modules
from .manifest_js import js_dependency_names, read_package_json
from .manifest_python import read_pyproject_toml_deps, read_requirements_txt


def all_declared_dependencies(repo: Path) -> set[str]:
    """Every dependency name/module path this repo declares across the
    three languages this tool understands, merged into one flat set of
    tokens to check against LOGGING_SIGNALS/TRACING_SIGNALS/
    METRICS_SIGNALS."""
    js_names = js_dependency_names(read_package_json(repo))
    py_names = read_requirements_txt(repo) | read_pyproject_toml_deps(repo)
    go_names = read_go_mod_modules(repo)
    return js_names | py_names | go_names


def detect_logging_libs(all_deps: set[str]) -> set[str]:
    return {LOGGING_SIGNALS[name] for name in all_deps if name in LOGGING_SIGNALS}


def detect_tracing_libs(all_deps: set[str]) -> set[str]:
    return {TRACING_SIGNALS[name] for name in all_deps if name in TRACING_SIGNALS}


def detect_metrics_libs(all_deps: set[str]) -> set[str]:
    return {METRICS_SIGNALS[name] for name in all_deps if name in METRICS_SIGNALS}
