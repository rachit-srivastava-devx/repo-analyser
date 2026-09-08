"""Supply-chain security: Trivy (Aqua Security) for infrastructure-as-code
misconfiguration scanning and SBOM generation. Two capabilities, deliberately
scoped to what nothing else in this tool already covers:

- `trivy config`: Dockerfile/Kubernetes/Terraform/CloudFormation
  misconfigurations (e.g. a container running as root, a Dockerfile with no
  HEALTHCHECK). Nothing else here checks infrastructure config at all.
- `trivy fs --format cyclonedx`: a standards-compliant CycloneDX SBOM per
  repo, saved as a real artifact (not reshaped into a repo-analyser-specific
  CSV -- an SBOM's value is being a standard format other tools can consume
  directly, e.g. Dependency-Track).

Explicitly NOT using Trivy's own vulnerability-scanning mode (`trivy fs`
without SBOM output, or `trivy image`): deps_audit.py already owns known-CVE
auditing via osv-scanner, reading the same lockfiles. Running Trivy's CVE
scanner too would duplicate that finding set under a different tool name,
not add new signal -- the same reuse-check this codebase already applies
elsewhere (see deps_audit.py's own docstring on why `npm audit` was dropped
once osv-scanner covered the same ground).

Grounded against the installed trivy 0.74.0's real JSON output (not
guessed): `trivy config` only lists FAILED checks in `Misconfigurations`
(passes are a bare count in `MisconfSummary.Successes`, not itemized) and
CycloneDX's `components` array needs a real lockfile present to produce
anything -- a bare `package.json` with no `package-lock.json` yields zero
components, the same lockfile-only limitation deps_audit.py already has.

`trivy config` passes `--skip-check-update`: before scanning anything,
trivy tries to verify its embedded misconfig-check bundle against an OCI
registry, and on a host where that lookup can't complete cleanly (no
working credential helper, or blocked egress) it hangs rather than failing
fast -- confirmed live: `trivy config` on a two-line Dockerfile hung
indefinitely while `--debug` showed it stuck before any scan started, only
proceeding once an external signal cancelled the OCI call, at which point
it fell back to embedded checks and finished the actual scan in ~1s. Left
unpatched, this eats the whole `run()` timeout above and the call gets
SIGKILLed before trivy ever falls back to its embedded checks, so
`_trivy_config_repo` returns zero misconfigs -- not because DS-0002 or any
other check stopped firing, but because the scan itself never ran. See
docs/METHODOLOGY.md's bug log.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.util import run, write_csv, write_json


@dataclass
class MisconfigFinding:
    repo: str
    id: str
    title: str
    severity: str
    target: str
    start_line: int
    message: str
    resolution: str


def _trivy_config_repo(repo: Path, tmp_dir: Path) -> list[MisconfigFinding]:
    report = tmp_dir / f"{repo.name}.trivy-config.json"
    run(["trivy", "config", str(repo), "--format", "json", "--output", str(report), "--quiet",
         "--skip-check-update"],
        check=False, timeout=180)
    if not report.exists() or not report.read_text().strip():
        return []
    data = json.loads(report.read_text())
    out = []
    for result in data.get("Results", []):
        target = result.get("Target", "")
        for m in result.get("Misconfigurations", []):
            cause = m.get("CauseMetadata", {}) or {}
            out.append(MisconfigFinding(
                repo=repo.name, id=m.get("ID", ""), title=m.get("Title", ""),
                severity=m.get("Severity", "UNKNOWN"), target=target,
                start_line=cause.get("StartLine", 0),
                message=m.get("Message", "")[:200], resolution=m.get("Resolution", "")[:200],
            ))
    return out


def _trivy_sbom_repo(repo: Path, sbom_dir: Path) -> tuple[Path | None, int]:
    """Returns (sbom file path or None if nothing was produced, component count)."""
    out_path = sbom_dir / f"{repo.name}.cyclonedx.json"
    run(["trivy", "fs", str(repo), "--format", "cyclonedx", "--output", str(out_path), "--quiet"],
        check=False, timeout=180)
    if not out_path.exists() or not out_path.read_text().strip():
        return None, 0
    data = json.loads(out_path.read_text())
    return out_path, len(data.get("components", []))


def run_supply_chain(repos: list[Path], out_dir: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sbom_dir = out_dir / "sbom"
    sbom_dir.mkdir(parents=True, exist_ok=True)

    misconfigs: list[MisconfigFinding] = []
    sbom_component_counts: dict[str, int] = {}
    errors: dict[str, str] = {}

    for r in repos:
        try:
            misconfigs.extend(_trivy_config_repo(r, tmp_dir))
        except Exception as e:  # noqa: BLE001 -- recorded per-repo, not swallowed
            errors[f"{r.name}:trivy-config"] = str(e)
        try:
            sbom_path, count = _trivy_sbom_repo(r, sbom_dir)
            if sbom_path is not None:
                sbom_component_counts[r.name] = count
        except Exception as e:  # noqa: BLE001
            errors[f"{r.name}:trivy-sbom"] = str(e)

    misconfig_path = out_dir / "supply_chain_misconfigs.csv"
    write_csv(misconfig_path, [asdict(m) for m in misconfigs],
              fieldnames=list(MisconfigFinding.__annotations__.keys()))

    if errors:
        write_json(out_dir / "supply_chain_errors.json", errors)

    sev_counts: dict[str, int] = {}
    for m in misconfigs:
        sev_counts[m.severity] = sev_counts.get(m.severity, 0) + 1
    write_json(out_dir / "supply_chain_summary.json", {
        "repos_scanned": len(repos),
        "total_misconfigs": len(misconfigs),
        "misconfigs_by_severity": sev_counts,
        "repos_with_misconfigs": len({m.repo for m in misconfigs}),
        "repos_with_sbom_generated": len(sbom_component_counts),
        "sbom_component_counts_by_repo": sbom_component_counts,
        "errors": len(errors),
    })
    return misconfig_path
