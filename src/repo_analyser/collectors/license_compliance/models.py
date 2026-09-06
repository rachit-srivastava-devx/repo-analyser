"""Result shape for the license_compliance collector -- one row per repo."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LicenseComplianceResult:
    repo: str
    license_file: str
    license_id: str
    manifest_declared_licenses: str
    license_mismatch: bool
    has_dependencies_no_license: bool
    detection_notes: str
