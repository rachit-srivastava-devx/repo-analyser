"""License compliance: repo-root LICENSE-file detection plus each present
manifest's own self-declared license, so a per-repo digest can flag a
missing license, an unrecognized license text, or a mismatch between what
the LICENSE file says and what a manifest claims.

v1 scope is deliberately pure static text/manifest analysis -- zero installs,
zero network calls. It does NOT run license-checker, pip-licenses,
go-licenses, or cargo-license: those require resolving the target repo's
own third-party dependency tree (npm install / pip install / go mod
download / cargo fetch), which crosses this repo's own gate on new external
tool dependencies that also need the target's own toolchain and network
access (AGENTS.md SS2 reuse-check, SS8 stop conditions -- this tool is
keyless by design and stays fully local/offline). Full third-party
dependency license auditing is out of scope for this collector.

See detect_license_file.py for the LICENSE-file precedence search,
spdx_match.py for the static text-signature table, manifest_licenses.py
(and its manifest_json_licenses.py / manifest_toml_licenses.py helpers) for
each manifest's own declared-license field, and analyze.py for how the two
are compared.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import LicenseComplianceResult
from .runner import run_license_compliance

__all__ = [
    "LicenseComplianceResult",
    "analyze_repo",
    "run_license_compliance",
]
