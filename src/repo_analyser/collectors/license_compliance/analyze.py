"""Wires LICENSE-file detection, SPDX matching, and manifest-declared
license extraction into one per-repo result."""
from __future__ import annotations

from pathlib import Path

from .detect_license_file import find_license_file, read_license_text
from .manifest_licenses import collect_manifest_declared_licenses
from .models import LicenseComplianceResult
from .spdx_match import match_spdx_id

DEPENDENCY_MANIFESTS = ("package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod")
_SEE_LICENSE_IN_PREFIX = "see license in"


def _is_file_pointer(declared: str) -> bool:
    """npm's documented "SEE LICENSE IN <file>" convention points at a
    file, not an SPDX id -- comparing it against a detected SPDX id would
    be a systematic false-positive mismatch for a common, legitimate
    real-world pattern, so it is excluded from the mismatch comparison."""
    return declared.strip().lower().startswith(_SEE_LICENSE_IN_PREFIX)


def analyze_repo(repo: Path) -> LicenseComplianceResult:
    license_path = find_license_file(repo)
    license_id = match_spdx_id(read_license_text(license_path)) if license_path else "unknown"
    declared = collect_manifest_declared_licenses(repo)
    comparable = [d for d in declared if not _is_file_pointer(d)]

    mismatch = bool(
        license_path is not None
        and license_id != "unknown"
        and any(d.strip().lower() != license_id.lower() for d in comparable)
    )
    has_manifest = any((repo / m).is_file() for m in DEPENDENCY_MANIFESTS)
    has_dependencies_no_license = has_manifest and license_path is None

    notes = [
        f"license file: {license_path.name}" if license_path else "no LICENSE file found",
        f"declared: {', '.join(declared)}" if declared else "no manifest-declared license",
    ]
    if mismatch:
        notes.append("mismatch between LICENSE file and manifest declaration")
    if has_dependencies_no_license:
        notes.append("dependency manifest present but no LICENSE file")

    return LicenseComplianceResult(
        repo=str(repo),
        license_file=license_path.name if license_path else "",
        license_id=license_id,
        manifest_declared_licenses="; ".join(declared),
        license_mismatch=mismatch,
        has_dependencies_no_license=has_dependencies_no_license,
        detection_notes="; ".join(notes),
    )
