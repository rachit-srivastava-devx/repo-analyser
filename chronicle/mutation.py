"""Mutation testing via Stryker (JS/TS): injects synthetic bugs and checks
whether the test suite actually catches them -- the real answer to "is test
coverage meaningful," which passing-test-count alone cannot answer (a file
can have passing tests that assert nothing that would catch a real defect;
see docs/METHODOLOGY.md for a real example this tool found).

Scoped deliberately, not exhaustively: only repos with a fully-passing unit
suite (testquality.py's output) are mutated -- a failing suite has no
meaningful mutation-score baseline. Only the repo's single highest
complexity x churn hotspot (complexity.py's output) is mutated, not the
whole codebase, to keep runtime bounded (each repo needs its own local
Stryker install, ~15-90s, plus the mutation run itself).

This module exists because of a real, hard-won install recipe -- three
earlier attempts (see docs/METHODOLOGY.md) failed on npx package
isolation, a missing typescript peer resolution, and a stale cached binary
name collision. The recipe that actually works, encoded here:
  1. Real local install (`npm install --no-save`, not `npx`) with
     `--legacy-peer-deps` (Stryker's own peer deps routinely conflict with
     a project's pinned eslint/typescript versions).
  2. Invoke the installed `node_modules/.bin/stryker` binary directly, not
     `npx stryker` (npx can resolve a stale/wrong cached package under
     that exact bin name).
  3. Pass through the project's own `jest.config.js` via Stryker's
     `jest.configFile` option, AND set whatever environment variable that
     config needs to select its unit-test testMatch pattern (this
     portfolio's jest configs gate `testMatch` on `TEST_TYPE=unit`; a
     config that conditions its test pattern on an env var will report
     "no tests found" otherwise, not an error naming the real cause).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from .util import run, write_csv, write_json


@dataclass
class MutationResult:
    repo: str
    file_mutated: str
    total_mutants: int
    killed: int
    survived: int
    no_coverage: int
    timeout: int
    mutation_score: float
    ran: bool
    skip_reason: str = ""


def _node20_bin() -> str | None:
    if os.environ.get("CHRONICLE_NODE_BIN"):
        return os.environ["CHRONICLE_NODE_BIN"]
    nvm_versions = Path.home() / ".nvm" / "versions" / "node"
    if nvm_versions.is_dir():
        candidates = sorted(nvm_versions.glob("v20.*"), reverse=True)
        if candidates:
            return str(candidates[0] / "bin")
    return None


NODE20_BIN = _node20_bin()


def _install_stryker(repo: Path) -> bool:
    binary = repo / "node_modules" / ".bin" / "stryker"
    if binary.exists():
        return True
    res = run(["npm", "install", "--no-audit", "--no-fund", "--no-save", "--legacy-peer-deps",
               "@stryker-mutator/core", "@stryker-mutator/jest-runner"],
              cwd=repo, check=False, timeout=180, extra_path=NODE20_BIN)
    return res.returncode == 0 and binary.exists()


def analyze_repo(repo: Path, target_file: str, jest_config: str = "jest.config.js",
                  test_type_env: str = "unit", tmp_dir: Path = Path("/tmp/chronicle_stryker")) -> MutationResult:
    if not (repo / target_file).exists():
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"target file not found: {target_file}")
    if not _install_stryker(repo):
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason="stryker install failed (see npm log)")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_dir / f"{repo.name}.stryker.json"
    report_dir = tmp_dir / f"{repo.name}-report"
    config = {
        "packageManager": "npm", "testRunner": "jest",
        "jest": {"projectType": "custom", "configFile": jest_config, "enableFindRelatedTests": False},
        "mutate": [target_file], "reporters": ["json"],
        "concurrency": 2, "timeoutMS": 30000,
        "tempDirName": str(tmp_dir / f"{repo.name}-tmp"),
        "htmlReporter": {"fileName": str(report_dir / "report.html")},
    }
    config_path.write_text(json.dumps(config))

    import shutil
    env_extra = {test_type_env: "unit"} if test_type_env else {}
    binary = repo / "node_modules" / ".bin" / "stryker"
    proc_env = dict(os.environ)
    if NODE20_BIN:
        proc_env["PATH"] = f"{NODE20_BIN}:{proc_env.get('PATH', '')}"
    proc_env.update(env_extra)
    import subprocess
    res = subprocess.run([str(binary), "run", str(config_path)], cwd=repo, capture_output=True,
                          text=True, timeout=180, env=proc_env)
    combined = res.stdout + res.stderr
    if "No tests were executed" in combined:
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason="jest found no tests -- check test_type_env/jest_config")

    mutation_json = repo / "reports" / "mutation" / "mutation.json"
    if not mutation_json.exists():
        return MutationResult(repo.name, target_file, 0, 0, 0, 0, 0, 0.0, False,
                               skip_reason=f"no mutation.json produced -- see raw output: {combined[-500:]}")
    data = json.loads(mutation_json.read_text())
    statuses = [m["status"] for f in data.get("files", {}).values() for m in f.get("mutants", [])]
    killed = statuses.count("Killed")
    survived = statuses.count("Survived")
    no_cov = statuses.count("NoCoverage")
    timeout_n = statuses.count("Timeout")
    total = len(statuses)
    covered = killed + survived + timeout_n
    score = round(100 * killed / covered, 1) if covered else 0.0
    return MutationResult(repo.name, target_file, total, killed, survived, no_cov, timeout_n, score, True)


def run_mutation(targets: list[tuple[Path, str]], out_dir: Path, tmp_dir: Path) -> Path:
    """targets: list of (repo_path, relative_file_to_mutate)."""
    rows = [asdict(analyze_repo(repo, f, tmp_dir=tmp_dir)) for repo, f in targets]
    out_path = out_dir / "mutation_results.csv"
    write_csv(out_path, rows)
    ran = [r for r in rows if r["ran"]]
    write_json(out_dir / "mutation_summary.json", {
        "repos_attempted": len(rows), "repos_succeeded": len(ran),
        "mean_mutation_score": round(sum(r["mutation_score"] for r in ran) / len(ran), 1) if ran else None,
        "skip_reasons": {r["repo"]: r["skip_reason"] for r in rows if not r["ran"]},
    })
    return out_path
