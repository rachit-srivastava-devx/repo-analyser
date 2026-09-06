"""Where a flag *definition* can live, source #1: a small root-level config
file (`flags.json`, `flags.yaml`, `.flagsmith.json`) -- parsed as a flat or
nested mapping, collecting only its top-level keys as flag names. Source #2
is a source-level dict/object literal, handled by
flag_extraction.extract_dict_literal_definitions. Both funnel into
collect_defined_flags's one raw (non-deduped) list, so analyze.py can both
dedupe (the defined *set*) and report how much duplication there was
(duplicate_definition_count).

A malformed or unreadable config file is treated as zero definitions from
that file -- not a whole-repo failure -- per the brief's edge-case list.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .flag_extraction import extract_dict_literal_definitions

ROOT_DEFINITION_FILES = ("flags.json", "flags.yaml", ".flagsmith.json")


def _read_root_config_keys(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return []
    try:
        # Path(".flagsmith.json").suffix == ".json" (the leading dot makes
        # it a hidden file, not an extension-less one), so this one check
        # correctly routes both flags.json and .flagsmith.json to the JSON
        # parser and leaves flags.yaml for YAML.
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        return []
    return list(data.keys()) if isinstance(data, dict) else []


def collect_defined_flags(repo: Path, source_texts: list[str]) -> list[str]:
    raw: list[str] = []
    for filename in ROOT_DEFINITION_FILES:
        raw.extend(_read_root_config_keys(repo / filename))
    for text in source_texts:
        raw.extend(extract_dict_literal_definitions(text))
    return raw
