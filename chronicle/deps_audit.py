"""Dependency health: known-CVE audit (osv-scanner, Google's cross-
ecosystem OSV-database scanner) and package staleness (npm outdated:
current vs. wanted vs. latest). This is the "package oldness" and "proper
security audit beyond secret-scanning" category -- gitleaks/semgrep
(security.py) check committed secrets and code patterns; this module
checks whether the *dependencies themselves* are known-vulnerable or out
of date, a different question entirely.

`npm audit` was tried first and dropped: it hung/timed out repeatedly in
this environment (a live registry round-trip per repo), where osv-scanner
(reads the lockfile directly against a local OSV database snapshot) is
both faster and already confirmed working -- see docs/METHODOLOGY.md.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

from .util import run, write_csv, write_json


@dataclass
class CVEFinding:
    repo: str
    source: str  # "npm-audit" | "osv-scanner"
    package: str
    severity: str
    id: str
    fix_available: str


@dataclass
class OutdatedPackage:
    repo: str
    package: str
    current: str
    wanted: str
    latest: str


def _osv_scan(repo: Path) -> list[CVEFinding]:
    lockfiles = list(repo.glob("package-lock.json")) + list(repo.glob("yarn.lock")) + \
        list(repo.glob("go.sum")) + list(repo.glob("requirements.txt")) + list(repo.glob("Gemfile.lock"))
    if not lockfiles:
        return []
    res = run(["osv-scanner", "--format", "json", str(repo)], check=False, timeout=120)
    if not res.stdout.strip():
        return []
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return []
    out = []
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            info = pkg.get("package", {})
            # `groups[].max_severity` is a plain CVSS numeric score (e.g. "3.2");
            # `vulnerabilities[].severity[].score` is a full CVSS *vector string*
            # ("CVSS:3.1/AV:L/..."), not a number -- confirmed against real
            # osv-scanner output before picking which field to use for sorting.
            group_severity = {gid: g.get("max_severity", "unknown")
                               for g in pkg.get("groups", []) for gid in g.get("ids", [])}
            for vuln in pkg.get("vulnerabilities", []):
                vid = vuln.get("id", "?")
                out.append(CVEFinding(
                    repo=repo.name, source="osv-scanner", package=info.get("name", "?"),
                    severity=group_severity.get(vid, "unknown"), id=vid, fix_available="unknown",
                ))
    return out


def _npm_outdated(repo: Path) -> list[OutdatedPackage]:
    if not (repo / "package.json").exists():
        return []
    res = run(["npm", "outdated", "--json"], cwd=repo, check=False, timeout=60)
    if not res.stdout.strip():
        return []
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return []
    return [OutdatedPackage(repo=repo.name, package=name, current=v.get("current", "?"),
                              wanted=v.get("wanted", "?"), latest=v.get("latest", "?"))
            for name, v in data.items()]


def run_deps_audit(repos: list[Path], out_dir: Path) -> Path:
    all_cves: list[CVEFinding] = []
    all_outdated: list[OutdatedPackage] = []
    errors: dict[str, str] = {}
    for r in repos:
        try:
            all_cves.extend(_osv_scan(r))
        except Exception as e:  # noqa: BLE001
            errors[f"{r.name}:osv-scanner"] = str(e)
        try:
            all_outdated.extend(_npm_outdated(r))
        except Exception as e:  # noqa: BLE001
            errors[f"{r.name}:npm-outdated"] = str(e)

    cve_path = out_dir / "deps_cves.csv"
    write_csv(cve_path, [asdict(c) for c in all_cves],
              fieldnames=list(CVEFinding.__annotations__.keys()) if all_cves else None)
    outdated_path = out_dir / "deps_outdated.csv"
    write_csv(outdated_path, [asdict(o) for o in all_outdated],
              fieldnames=list(OutdatedPackage.__annotations__.keys()) if all_outdated else None)
    if errors:
        write_json(out_dir / "deps_audit_errors.json", errors)

    def _tier(score: str) -> str:
        try:
            f = float(score)
        except ValueError:
            return "unknown"
        if f >= 9.0:
            return "critical"
        if f >= 7.0:
            return "high"
        if f >= 4.0:
            return "medium"
        return "low"

    sev_counts: dict[str, int] = defaultdict(int)
    for c in all_cves:
        sev_counts[_tier(c.severity)] += 1
    by_repo_cve: dict[str, int] = defaultdict(int)
    for c in all_cves:
        by_repo_cve[c.repo] += 1
    major_behind = sum(1 for o in all_outdated
                        if o.current != "?" and o.latest != "?" and o.current.split(".")[0] != o.latest.split(".")[0])

    write_json(out_dir / "deps_audit_summary.json", {
        "total_cve_findings": len(all_cves),
        "cve_by_severity": dict(sev_counts),
        "repos_with_cves": len(by_repo_cve),
        "repos_with_cves_list": sorted(by_repo_cve, key=lambda k: -by_repo_cve[k]),
        "total_outdated_packages": len(all_outdated),
        "outdated_major_version_behind": major_behind,
    })
    return cve_path
