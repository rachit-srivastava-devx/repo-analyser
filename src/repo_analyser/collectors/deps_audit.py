"""Dependency health: known-CVE audit (osv-scanner, Google's cross-
ecosystem OSV-database scanner), package staleness (current vs. wanted vs.
latest -- npm outdated for JS, `pip list --outdated` for Python, `go list
-u -m` for Go), and license compliance (license-checker/pip-licenses/
go-licenses, flagging anything outside a small permissive allow-list).
This is the "package oldness", "proper security audit beyond
secret-scanning", and "are we legally allowed to ship these dependencies"
category -- gitleaks/semgrep (security.py) check committed secrets and
code patterns; this module checks whether the *dependencies themselves*
are known-vulnerable, out of date, or under a license this portfolio
hasn't cleared, three different questions entirely.

This is a different question from `collectors/license_compliance/`, which
reads *this repo's own* declared LICENSE file/manifest field (pure static
text/manifest parsing, zero installs -- see its own module docstring for
why it deliberately does not run license-checker/pip-licenses/go-licenses
itself). The license-compliance work here is about what license each
*third-party dependency* is under, which needs the target's already-
resolved dependency tree (node_modules / a venv / the module cache) to
answer at all -- a genuinely different mechanism and a genuinely
different question, not a second collector re-measuring the same thing
under a different name (AGENTS.md SS4).

`npm audit` was tried first and dropped: it hung/timed out repeatedly in
this environment (a live registry round-trip per repo), where osv-scanner
(reads the lockfile directly against a local OSV database snapshot) is
both faster and already confirmed working -- see docs/METHODOLOGY.md.

The allow-list below ({MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC})
is also the canonical definition docs/ROADMAP.md says a future
`deps_diff.py` (per-PR `--licenses` allowlist, PR-review wave 2, item
#21) must reconcile with rather than silently diverge from. `deps_diff.py`
does not exist on this branch yet (checked at the time this was written),
so there is nothing to reconcile against today -- whoever builds it should
import `LICENSE_ALLOWLIST` from here (or keep an identical set) instead of
redefining its own.

License-compliance and Python/Go staleness real-CLI-behavior notes (all
confirmed live against real installs in this environment, not guessed
from memory -- see this change's own report for the exact commands run):
  - `license-checker --json` (JS): also reports the analyzed repo's OWN
    package (keyed the same "name@version" way as a real dependency,
    license "UNKNOWN" when package.json has no `license` field) --
    excluded by resolving its `path` field against the repo root, not by
    name, since a scoped package name can itself contain "@". Confirmed
    live: a package.json with no `license` field reports exactly
    `"testrepo-js@1.0.0": {"licenses": "UNKNOWN", "path": "<repo root>"}`.
  - `pip-licenses --format=json` (Python): reports human-readable PyPI
    trove-classifier text by default, NOT SPDX ids, for many common
    packages (confirmed live: `requests` -> "Apache Software License",
    not "Apache-2.0"; `idna` -> "BSD-3-Clause", already exact) -- handled
    via a small, explicit, conservative alias table (`PIP_LICENSE_ALIASES`)
    covering only unambiguous cases; the classifier-only "BSD License"
    string (doesn't distinguish 2- vs 3-clause) is deliberately left out
    of the table, so it's flagged as a violation rather than silently
    guessed which BSD variant it is.
  - `go-licenses csv ./...` (Go): three columns, `name,license_url,
    license_name`, no header row, one row per library (per upstream
    github.com/google/go-licenses's report.go). UNVERIFIED live in this
    environment specifically: this machine's `go install`-built
    go-licenses binary crashes on every invocation (confirmed:
    `go-licenses --help` -> exit 134, empty stdout, stderr "dyld: missing
    LC_UUID load command") -- confirmed unrelated to the Go toolchain
    generally (`go build`/`go list` both work fine on this machine), so
    treated as a genuine tool failure (`ToolExecutionError` via `run()`'s
    default `check=True`), not a "found nothing" result. The CSV-parsing
    logic itself is exercised by unit tests against synthetic go-licenses-
    shaped output, not a live run.
  - `go list -u -m -json all` (Go staleness): output is concatenated
    pretty-printed JSON objects, NOT a JSON array or NDJSON -- parsed with
    `json.JSONDecoder.raw_decode` in a loop (confirmed against real
    output from a throwaway `go.mod`/`go.sum` fixture). The main module's
    own entry has `"Main": true` and no `Update` field -- excluded
    explicitly, not just by accident of lacking an update. Confirmed live
    that this can exit 1 with empty stdout (only a stderr toolchain-
    download warning) when the repo's declared `go` directive is newer
    than what's resolvable in this environment -- a realistic, common
    portfolio-wide version-skew condition, so (unlike go-licenses above)
    handled the same way `_osv_scan`/`_npm_outdated` already handle their
    own tools' non-zero exits: `check=False`, empty stdout means no
    findings for this repo.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ..core.util import run, run_concurrent, write_csv, write_json

# See module docstring: shared with (and must stay in sync with) any
# future deps_diff.py per-PR --licenses allowlist, per docs/ROADMAP.md.
LICENSE_ALLOWLIST = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"})

# pip-licenses' default `--format=json` reports PyPI trove-classifier
# text, not SPDX ids -- see module docstring for the live-confirmed
# examples. Only unambiguous 1:1 mappings go here; anything else (e.g.
# the classifier-only "BSD License", which doesn't say 2- vs 3-clause) is
# deliberately left unmapped so it gets flagged, not silently guessed.
PIP_LICENSE_ALIASES = {
    "Apache Software License": "Apache-2.0",
    "MIT License": "MIT",
    "ISC License (ISCL)": "ISC",
    "BSD 2-Clause License": "BSD-2-Clause",
    "BSD 3-Clause License": "BSD-3-Clause",
}


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
    ecosystem: str  # "js" | "python" | "go"
    package: str
    current: str
    wanted: str
    latest: str


@dataclass
class LicenseFinding:
    repo: str
    ecosystem: str  # "js" | "python" | "go"
    package: str
    license: str
    license_violation: bool


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
    return [OutdatedPackage(repo=repo.name, ecosystem="js", package=name, current=v.get("current", "?"),
                              wanted=v.get("wanted", "?"), latest=v.get("latest", "?"))
            for name, v in data.items()]


def _looks_python_repo(repo: Path) -> bool:
    return (repo / "requirements.txt").exists() or (repo / "pyproject.toml").exists() \
        or (repo / "setup.py").exists()


def _find_venv_binary(repo: Path, name: str) -> Path | None:
    """Prefer the target repo's own virtualenv over a bare PATH lookup --
    same principle as testquality.py's `_pytest_command`: a bare tool on
    PATH belongs to *this* process's environment, not necessarily the
    target repo's own installed dependencies, which would silently report
    the wrong packages' licenses/versions entirely rather than the target
    repo's."""
    for venv_dir in (".venv", "venv"):
        candidate = repo / venv_dir / "bin" / name
        if candidate.is_file():
            return candidate
    return None


def _pip_outdated(repo: Path) -> tuple[list[OutdatedPackage], str]:
    """Returns (findings, skip_reason). skip_reason is "" unless this
    looks like a Python repo but has no target-owned venv to check
    installed-package versions against."""
    if not _looks_python_repo(repo):
        return [], ""
    pip_bin = _find_venv_binary(repo, "pip")
    if pip_bin is None:
        return [], "no target-owned .venv/venv with pip found"
    res = run([str(pip_bin), "list", "--outdated", "--format=json"], cwd=repo, timeout=120)
    if not res.stdout.strip():
        return [], ""
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return [], ""
    return [OutdatedPackage(repo=repo.name, ecosystem="python", package=p.get("name", "?"),
                              current=p.get("version", "?"), wanted=p.get("version", "?"),
                              latest=p.get("latest_version", "?"))
            for p in data], ""


def _go_outdated(repo: Path) -> tuple[list[OutdatedPackage], str]:
    """Returns (findings, skip_reason). `go list -u -m -json all` emits
    concatenated pretty-printed JSON objects (not an array, not NDJSON) --
    see module docstring for the live-confirmed shape."""
    if not (repo / "go.mod").exists():
        return [], ""
    if not shutil.which("go"):
        return [], "go not found on PATH"
    res = run(["go", "list", "-u", "-m", "-json", "all"], cwd=repo, check=False, timeout=120)
    if not res.stdout.strip():
        # Confirmed live: exit 1 + empty stdout is the real shape of a
        # toolchain-version-skew failure (repo's `go` directive newer than
        # what's resolvable here) -- treated as no findings for this repo,
        # the same way `_osv_scan`/`_npm_outdated` already treat their own
        # tools' non-zero-exit-with-no-output case.
        return [], ""
    out = []
    decoder = json.JSONDecoder()
    text, idx, n = res.stdout, 0, len(res.stdout)
    while idx < n:
        while idx < n and text[idx].isspace():
            idx += 1
        if idx >= n:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        idx = end
        if obj.get("Main"):
            continue  # the analyzed repo's own module, not a dependency
        update = obj.get("Update")
        if not update:
            continue  # already at latest, or no update info published
        current = obj.get("Version", "?")
        # Go modules pin one exact version in go.mod; there is no separate
        # "wanted" concept the way npm's semver-range "wanted" is distinct
        # from "latest" -- current IS what's wanted until go.mod is bumped.
        out.append(OutdatedPackage(repo=repo.name, ecosystem="go", package=obj.get("Path", "?"),
                                     current=current, wanted=current, latest=update.get("Version", "?")))
    return out, ""


def _license_checker_js(repo: Path) -> tuple[list[LicenseFinding], str]:
    """Returns (findings, skip_reason). Only runs license-checker from the
    repo's own node_modules/.bin (see `_find_venv_binary`'s docstring for
    why a bare PATH tool would be the wrong environment's data)."""
    if not (repo / "package.json").exists():
        return [], ""
    binary = repo / "node_modules" / ".bin" / "license-checker"
    if not binary.is_file():
        return [], "license-checker not found in node_modules/.bin"
    res = run([str(binary), "--json"], cwd=repo, timeout=120)
    if not res.stdout.strip():
        return [], ""
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return [], ""
    repo_resolved = repo.resolve()
    out = []
    for key, info in data.items():
        pkg_path = info.get("path")
        if pkg_path and Path(pkg_path).resolve() == repo_resolved:
            continue  # the analyzed repo's own package, not a dependency
        name, _, _version = key.rpartition("@")
        licenses = info.get("licenses", "UNKNOWN")
        license_str = " OR ".join(licenses) if isinstance(licenses, list) else str(licenses)
        out.append(LicenseFinding(repo=repo.name, ecosystem="js", package=name or key,
                                    license=license_str, license_violation=license_str not in LICENSE_ALLOWLIST))
    return out, ""


def _pip_licenses_py(repo: Path) -> tuple[list[LicenseFinding], str]:
    """Returns (findings, skip_reason). Only runs pip-licenses from the
    target's own venv -- ROADMAP.md's explicit precondition, same one
    testquality.py's `_pytest_command` already documents."""
    if not _looks_python_repo(repo):
        return [], ""
    binary = _find_venv_binary(repo, "pip-licenses")
    if binary is None:
        return [], "no target-owned .venv/venv with pip-licenses found"
    res = run([str(binary), "--format=json"], cwd=repo, timeout=120)
    if not res.stdout.strip():
        return [], ""
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return [], ""
    out = []
    for entry in data:
        raw = entry.get("License", "UNKNOWN")
        norm = PIP_LICENSE_ALIASES.get(raw, raw)
        out.append(LicenseFinding(repo=repo.name, ecosystem="python", package=entry.get("Name", "?"),
                                    license=norm, license_violation=norm not in LICENSE_ALLOWLIST))
    return out, ""


def _go_licenses_go(repo: Path) -> tuple[list[LicenseFinding], str]:
    """Returns (findings, skip_reason). `go-licenses csv ./...` -> 3
    headerless columns, `name,license_url,license_name`, per upstream
    report.go -- see module docstring for the live-confirmed availability
    caveat on this machine specifically."""
    if not (repo / "go.mod").exists():
        return [], ""
    if not shutil.which("go-licenses"):
        return [], "go-licenses not found on PATH"
    res = run(["go-licenses", "csv", "./..."], cwd=repo, timeout=180)
    out = []
    for row in csv.reader(io.StringIO(res.stdout)):
        if len(row) != 3:
            continue
        name, _url, license_name = row
        out.append(LicenseFinding(repo=repo.name, ecosystem="go", package=name, license=license_name,
                                    license_violation=license_name not in LICENSE_ALLOWLIST))
    return out, ""


def _severity_tier(score: str) -> str:
    """CVSS score -> tier bucket. `score` is a string because osv-scanner's
    `max_severity` field is a numeric CVSS score serialized as a JSON
    string ("3.2") -- a non-numeric/missing value (osv-scanner emits
    "unknown" for a vuln with no CVSS score at all) is a real, expected
    input, not a malformed one, so it maps to "unknown" rather than raising."""
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


def _audit_one_repo(
    r: Path,
) -> tuple[list[CVEFinding], list[OutdatedPackage], list[LicenseFinding], dict[str, str], dict[str, str]]:
    all_cves: list[CVEFinding] = []
    all_outdated: list[OutdatedPackage] = []
    all_licenses: list[LicenseFinding] = []
    errors: dict[str, str] = {}
    skips: dict[str, str] = {}

    try:
        all_cves.extend(_osv_scan(r))
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:osv-scanner"] = str(e)

    try:
        all_outdated.extend(_npm_outdated(r))
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:npm-outdated"] = str(e)
    try:
        outdated, skip = _pip_outdated(r)
        all_outdated.extend(outdated)
        if skip:
            skips[f"{r.name}:pip-outdated"] = skip
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:pip-outdated"] = str(e)
    try:
        outdated, skip = _go_outdated(r)
        all_outdated.extend(outdated)
        if skip:
            skips[f"{r.name}:go-outdated"] = skip
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:go-outdated"] = str(e)

    try:
        licenses, skip = _license_checker_js(r)
        all_licenses.extend(licenses)
        if skip:
            skips[f"{r.name}:license-checker"] = skip
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:license-checker"] = str(e)
    try:
        licenses, skip = _pip_licenses_py(r)
        all_licenses.extend(licenses)
        if skip:
            skips[f"{r.name}:pip-licenses"] = skip
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:pip-licenses"] = str(e)
    try:
        licenses, skip = _go_licenses_go(r)
        all_licenses.extend(licenses)
        if skip:
            skips[f"{r.name}:go-licenses"] = skip
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
        errors[f"{r.name}:go-licenses"] = str(e)

    return all_cves, all_outdated, all_licenses, errors, skips


def run_deps_audit(repos: list[Path], out_dir: Path) -> Path:
    all_cves: list[CVEFinding] = []
    all_outdated: list[OutdatedPackage] = []
    all_licenses: list[LicenseFinding] = []
    errors: dict[str, str] = {}
    skips: dict[str, str] = {}
    # each repo's CVE/staleness/license signals are independent, I/O-bound
    # subprocess calls -- see core.util.run_concurrent's docstring.
    for repo_cves, repo_outdated, repo_licenses, repo_errors, repo_skips in run_concurrent(repos, _audit_one_repo):
        all_cves.extend(repo_cves)
        all_outdated.extend(repo_outdated)
        all_licenses.extend(repo_licenses)
        errors.update(repo_errors)
        skips.update(repo_skips)

    cve_path = out_dir / "deps_cves.csv"
    write_csv(cve_path, [asdict(c) for c in all_cves], fieldnames=list(CVEFinding.__annotations__.keys()))
    outdated_path = out_dir / "deps_outdated.csv"
    write_csv(outdated_path, [asdict(o) for o in all_outdated],
              fieldnames=list(OutdatedPackage.__annotations__.keys()))
    licenses_path = out_dir / "deps_licenses.csv"
    write_csv(licenses_path, [asdict(lic) for lic in all_licenses],
              fieldnames=list(LicenseFinding.__annotations__.keys()))
    if errors:
        write_json(out_dir / "deps_audit_errors.json", errors)
    if skips:
        write_json(out_dir / "deps_audit_skips.json", skips)

    sev_counts: dict[str, int] = defaultdict(int)
    for c in all_cves:
        sev_counts[_severity_tier(c.severity)] += 1
    by_repo_cve: dict[str, int] = defaultdict(int)
    for c in all_cves:
        by_repo_cve[c.repo] += 1
    major_behind = sum(1 for o in all_outdated
                        if o.current != "?" and o.latest != "?" and o.current.split(".")[0] != o.latest.split(".")[0])

    by_repo_license_violation: dict[str, int] = defaultdict(int)
    for lic in all_licenses:
        if lic.license_violation:
            by_repo_license_violation[lic.repo] += 1
    license_violations = sum(1 for lic in all_licenses if lic.license_violation)

    write_json(out_dir / "deps_audit_summary.json", {
        "total_cve_findings": len(all_cves),
        "cve_by_severity": dict(sev_counts),
        "repos_with_cves": len(by_repo_cve),
        "repos_with_cves_list": sorted(by_repo_cve, key=lambda k: -by_repo_cve[k]),
        "total_outdated_packages": len(all_outdated),
        "outdated_major_version_behind": major_behind,
        "total_license_findings": len(all_licenses),
        "license_violations": license_violations,
        "repos_with_license_violations": len(by_repo_license_violation),
        "repos_with_license_violations_list": sorted(by_repo_license_violation,
                                                       key=lambda k: -by_repo_license_violation[k]),
    })
    return cve_path
