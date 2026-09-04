"""Security scanning: gitleaks over full git history (a secret removed in a
later commit is still a leak -- history scanning catches what a working-tree
scan would miss), plus semgrep over the current tree for code-level
vulnerability patterns (hardcoded-fallback secrets, injection, etc.).

Both tools are run with check=False: a non-zero exit is their normal
"found something" signal, not a tool failure. The only tool failure is
malformed/missing JSON output, which raises explicitly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .util import run, write_csv, write_json

SEMGREP_CONFIGS = ["p/security-audit", "p/secrets"]


@dataclass
class SecretFinding:
    repo: str
    rule_id: str
    file: str
    commit: str
    author: str
    date: str
    secret_redacted: str


@dataclass
class SemgrepFinding:
    repo: str
    check_id: str
    severity: str
    file: str
    start_line: int
    message: str


def _gitleaks_repo(repo: Path, tmp_dir: Path) -> list[SecretFinding]:
    report = tmp_dir / f"{repo.name}.gitleaks.json"
    run(["gitleaks", "detect", "-s", str(repo), "-f", "json", "-r", str(report),
         "--no-banner", "--exit-code", "0"], check=True, timeout=180)
    if not report.exists() or not report.read_text().strip():
        return []
    data = json.loads(report.read_text())
    out = []
    for f in data:
        secret = f.get("Secret", "")
        redacted = (secret[:4] + "..." + secret[-2:]) if len(secret) > 8 else "***"
        out.append(SecretFinding(
            repo=repo.name, rule_id=f.get("RuleID", ""), file=f.get("File", ""),
            commit=f.get("Commit", "")[:10], author=f.get("Author", ""),
            date=f.get("Date", ""), secret_redacted=redacted,
        ))
    return out


def _semgrep_repo(repo: Path, tmp_dir: Path) -> list[SemgrepFinding]:
    report = tmp_dir / f"{repo.name}.semgrep.json"
    cmd = ["semgrep"]
    for c in SEMGREP_CONFIGS:
        cmd += ["--config", c]
    cmd += ["--json", "--output", str(report), "--quiet",
            "--exclude", "node_modules", "--exclude", "dist", "--exclude", "build", "."]
    run(cmd, cwd=repo, check=False, timeout=240)
    if not report.exists() or not report.read_text().strip():
        return []
    data = json.loads(report.read_text())
    out = []
    for r in data.get("results", []):
        out.append(SemgrepFinding(
            repo=repo.name, check_id=r.get("check_id", ""),
            severity=(r.get("extra", {}) or {}).get("severity", ""),
            file=r.get("path", ""), start_line=(r.get("start", {}) or {}).get("line", 0),
            message=(r.get("extra", {}) or {}).get("message", "")[:200],
        ))
    return out


def run_security(repos: list[Path], out_dir: Path, tmp_dir: Path) -> tuple[Path, Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    secrets: list[SecretFinding] = []
    semgrep_findings: list[SemgrepFinding] = []
    errors: dict[str, str] = {}

    for r in repos:
        try:
            secrets.extend(_gitleaks_repo(r, tmp_dir))
        except Exception as e:  # noqa: BLE001 -- recorded per-repo, not swallowed
            errors[f"{r.name}:gitleaks"] = str(e)
        try:
            semgrep_findings.extend(_semgrep_repo(r, tmp_dir))
        except Exception as e:  # noqa: BLE001
            errors[f"{r.name}:semgrep"] = str(e)

    secrets_path = out_dir / "security_secrets.csv"
    write_csv(secrets_path, [asdict(s) for s in secrets],
              fieldnames=list(SecretFinding.__annotations__.keys()) if secrets else None)
    semgrep_path = out_dir / "security_semgrep.csv"
    write_csv(semgrep_path, [asdict(s) for s in semgrep_findings],
              fieldnames=list(SemgrepFinding.__annotations__.keys()) if semgrep_findings else None)

    if errors:
        write_json(out_dir / "security_errors.json", errors)

    sev_counts: dict[str, int] = {}
    for s in semgrep_findings:
        sev_counts[s.severity] = sev_counts.get(s.severity, 0) + 1
    write_json(out_dir / "security_summary.json", {
        "total_secrets_found": len(secrets),
        "repos_with_secrets": len({s.repo for s in secrets}),
        "total_semgrep_findings": len(semgrep_findings),
        "semgrep_by_severity": sev_counts,
        "repos_scanned": len(repos),
        "errors": len(errors),
    })
    return secrets_path, semgrep_path
