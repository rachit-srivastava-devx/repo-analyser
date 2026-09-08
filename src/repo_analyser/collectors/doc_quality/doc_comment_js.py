"""Doc-comment coverage, JS/TS: no keyless CLI tool measures real JSDoc
coverage %, so this is a weaker, presence-only signal instead --
`eslint-plugin-jsdoc` present in package.json `devDependencies` AND some
eslint config file textually referencing `jsdoc` (a plain substring/word-
boundary grep of the config file's raw text, not a real parse of a
JS-flat-config's executable expressions or a JSON rules tree -- config
formats vary too much to parse precisely here, matching this codebase's
existing precedent for where live measurement isn't practical, e.g.
performance.py's own config-file-presence checks). This is NOT a
percentage; `doc_comment_coverage_pct` stays 0.0 (sentinel) for these
rows and the real signal lives entirely in `doc_comment_tool` -- don't
read a JS/TS repo's 0.0 as "0% documented", check `doc_comment_tool`
first."""
from __future__ import annotations

import json
from pathlib import Path

from .models import ESLINT_CONFIG_FILENAMES, JSDOC_REF_RE


def _read_package_json(repo: Path) -> dict:
    pj = repo / "package.json"
    if not pj.exists():
        return {}
    try:
        return json.loads(pj.read_text())
    except json.JSONDecodeError:
        return {}


def _js_doc_comment_signal(repo: Path) -> tuple[float, str, str]:
    """Presence-only JS/TS signal -- see module docstring. Returns
    (coverage_pct, tool, skip_reason); coverage_pct is always 0.0 (never a
    real measurement) here."""
    pkg = _read_package_json(repo)
    has_dep = "eslint-plugin-jsdoc" in (pkg.get("devDependencies") or {})

    config_text_parts = []
    for name in ESLINT_CONFIG_FILENAMES:
        p = repo / name
        if not p.exists():
            continue
        try:
            config_text_parts.append(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    has_config_ref = bool(JSDOC_REF_RE.search("\n".join(config_text_parts)))

    if has_dep and has_config_ref:
        return 0.0, "eslint-plugin-jsdoc", ""
    if has_dep and not has_config_ref:
        return 0.0, "", "eslint-plugin-jsdoc is a devDependency but no eslint config file references jsdoc rules"
    if has_config_ref and not has_dep:
        return 0.0, "", "an eslint config references jsdoc but eslint-plugin-jsdoc is not a package.json devDependency"
    return 0.0, "", "no eslint-plugin-jsdoc devDependency or jsdoc-referencing eslint config found"
