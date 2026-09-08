"""Shared test-fixture builders for notebook_quality's test package."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


def nb(cells: list[dict]) -> str:
    """Serializes a real nbformat v4 envelope around the given cells --
    the actual on-disk shape, not a simplified stand-in."""
    return json.dumps({
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    })


def code_cell(source: list[str], execution_count: int | None = None, outputs: list[dict] | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": execution_count,
        "metadata": {},
        "outputs": outputs if outputs is not None else [],
        "source": source,
    }


def markdown_cell(source: list[str]) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}
