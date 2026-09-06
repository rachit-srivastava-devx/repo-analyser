"""Per-repo dead-code analysis: dispatches to vulture (python) and the JS/TS
heuristic, and applies this collector's None-vs-zero contract (see
models.DeadCodeResult's docstring)."""
from __future__ import annotations

from pathlib import Path

from .js_heuristic import js_ts_files, scan_repo
from .models import FINDINGS_CAP, DeadCodeResult, Finding
from .vulture_runner import has_python_files, run_vulture, vulture_available


def analyze_repo(repo: Path) -> DeadCodeResult:
    tool_unavailable: list[str] = []
    findings: list[Finding] = []

    dead_code_items_python: int | None = None
    if has_python_files(repo):
        if not vulture_available():
            tool_unavailable.append("vulture")
        else:
            try:
                py_findings = run_vulture(repo)
            except Exception:  # noqa: BLE001 -- a subprocess failure (timeout,
                # a TOCTOU race on the PATH check) on this one repo must not
                # crash the whole portfolio run, and must not look identical
                # to "ran clean, found nothing" -- naming "vulture" here
                # keeps the None visible as "couldn't check", not "checked,
                # zero found". Deep diagnosis of *why* belongs to the run's
                # own top-level error log, not a per-repo field here.
                tool_unavailable.append("vulture")
            else:
                dead_code_items_python = len(py_findings)
                findings.extend(py_findings)

    unreferenced_export_count_js: int | None = None
    js_files = js_ts_files(repo)
    if js_files:
        js_findings = scan_repo(repo, js_files)
        unreferenced_export_count_js = len(js_findings)
        findings.extend(js_findings)

    # Python findings first, then JS -- so a Python-heavy repo's cap may
    # crowd out JS findings entirely from the *detail* list. The two count
    # fields above are unaffected: they are always the true, uncapped
    # counts. Simplest reading of "cap at ~50", not a fairness guarantee
    # between languages -- the brief did not ask for one.
    return DeadCodeResult(
        repo=repo.name,
        dead_code_items_python=dead_code_items_python,
        unreferenced_export_count_js=unreferenced_export_count_js,
        findings=findings[:FINDINGS_CAP],
        tool_unavailable=tool_unavailable,
    )
