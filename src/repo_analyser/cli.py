#!/usr/bin/env python3
"""Repo Analyser CLI.

Usage:
    repo-analyser analyze <target> [--out DIR] [--modules a,b,c] [--skip-slow]
    repo-analyser list-modules
    repo-analyser report <out_dir>

(or, without installing: `python3 -m repo_analyser analyze ...`)

<target> is either a single git repo, or a directory containing one or more
git repos as immediate children (a portfolio -- e.g. an org's repos cloned
side by side). Each module writes its own CSV/JSON into --out (default:
./analyses/<target-name>/) so any number in the final report can be traced
back to raw, re-runnable data.
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

from .core.util import discover_repos, read_json, write_json

MODULES = [
    "inventory", "ci_gates", "ontology", "effort", "escape", "churn", "complexity",
    "duplication", "exact_duplicates", "security", "depgraph", "testquality", "e2e_quality",
    "performance", "deps_audit", "supply_chain", "lint_quality", "code_quality", "mutation",
    "knowledge_graph", "synthesize", "trends", "per_repo_digest", "deep_reports", "exec_deck", "pdf",
]
SLOW_MODULES = {"escape", "churn", "complexity", "duplication", "exact_duplicates", "security", "depgraph",
                 "testquality", "deps_audit", "supply_chain", "lint_quality", "mutation"}


def run_module(name: str, repos: list[Path], target: Path, out_dir: Path, tmp_dir: Path) -> dict:
    t0 = time.time()
    try:
        if name == "inventory":
            from .collectors.inventory import run_inventory
            run_inventory(repos, out_dir)
        elif name == "ci_gates":
            from .collectors.ci_gates import run_ci_gates
            run_ci_gates(repos, out_dir)
        elif name == "ontology":
            from .collectors.ontology import run_ontology
            run_ontology(repos, out_dir)
        elif name == "escape":
            from .collectors.escape import run_escape
            run_escape(repos, out_dir)
        elif name == "churn":
            from .collectors.churn import run_churn
            run_churn(repos, out_dir, tmp_dir / "maat_logs")
        elif name == "complexity":
            from .collectors.complexity import run_complexity
            run_complexity(repos, out_dir, churn_csv=out_dir / "churn_revisions.csv")
        elif name == "duplication":
            from .collectors.duplication import run_duplication
            run_duplication(target, out_dir, repos=repos)
        elif name == "exact_duplicates":
            from .collectors.exact_duplicates import run_exact_duplicates
            run_exact_duplicates(repos, out_dir)
        elif name == "security":
            from .collectors.security import run_security
            run_security(repos, out_dir, tmp_dir / "security")
        elif name == "depgraph":
            from .collectors.depgraph import run_depgraph
            run_depgraph(repos, out_dir)
        elif name == "testquality":
            from .collectors.testquality import run_testquality
            run_testquality(repos, out_dir, tmp_dir / "testquality_logs")
        elif name == "e2e_quality":
            from .collectors.e2e_quality import run_e2e_quality
            run_e2e_quality(repos, out_dir)
        elif name == "performance":
            from .collectors.performance import run_performance
            run_performance(repos, out_dir)
        elif name == "knowledge_graph":
            from .graph.knowledge_graph import run_knowledge_graph
            run_knowledge_graph(out_dir, target, out_dir)
        elif name == "deps_audit":
            from .collectors.deps_audit import run_deps_audit
            run_deps_audit(repos, out_dir)
        elif name == "supply_chain":
            from .collectors.supply_chain import run_supply_chain
            run_supply_chain(repos, out_dir, tmp_dir / "supply_chain")
        elif name == "lint_quality":
            from .collectors.lint_quality import run_lint_quality
            run_lint_quality(repos, out_dir)
        elif name == "code_quality":
            from .collectors.code_quality import run_code_quality
            run_code_quality(repos, out_dir)
        elif name == "mutation":
            from .collectors.mutation import run_mutation, select_mutation_targets
            targets = select_mutation_targets(out_dir, repos)
            run_mutation(targets, out_dir, tmp_dir / "mutation")
        elif name == "effort":
            from .collectors.effort import run_effort
            run_effort(out_dir / "ontology_commits.csv", out_dir)
        elif name == "synthesize":
            from .synthesis.synthesize import run_synthesize
            run_synthesize([r.name for r in repos], out_dir)
        elif name == "per_repo_digest":
            from .synthesis.per_repo_digest import run_per_repo_digest
            run_per_repo_digest(out_dir, out_dir / "deep" / "per-repo", [r.name for r in repos],
                                 target.resolve().name)
        elif name == "trends":
            from .synthesis.trends import run_trends
            run_trends(out_dir, [r.name for r in repos])
        elif name == "deep_reports":
            from .synthesis.deep_reports import generate_all
            generate_all(out_dir, out_dir / "deep", target.resolve().name)
        elif name == "exec_deck":
            from .synthesis.exec_deck import run_exec_deck
            run_exec_deck(out_dir, target.resolve().name)
        elif name == "pdf":
            from .reporting.pdf_export import build_pdf
            deep_dir = out_dir / "deep"
            if not deep_dir.exists():
                raise FileNotFoundError("run the deep_reports module before pdf")
            build_pdf(deep_dir, deep_dir / f"{target.resolve().name}-analysis-report.pdf",
                      f"The {target.resolve().name} Portfolio, <em>Measured</em>")
        else:
            raise ValueError(f"unknown module: {name}")
        return {"module": name, "status": "ok", "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:  # noqa: BLE001 -- recorded, not swallowed; run continues to next module
        return {
            "module": name, "status": "error", "elapsed_s": round(time.time() - t0, 1),
            "error": str(e), "traceback": traceback.format_exc(),
        }


def cmd_analyze(args: argparse.Namespace) -> int:
    target = Path(args.target)
    repos = discover_repos(target)  # raises with a clear message if target is unusable
    is_portfolio = len(repos) > 1 or repos[0] != target.resolve()
    out_dir = Path(args.out) if args.out else Path("analyses") / target.resolve().name
    tmp_dir = out_dir / "_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)

    prior_run_log: list[dict] = []
    if args.retry_failed:
        run_log_path = out_dir / "run_log.json"
        if not run_log_path.exists():
            print(f"--retry-failed requires an existing run_log.json in {out_dir} (no prior run found here)",
                  file=sys.stderr)
            return 2
        prior_run_log = read_json(run_log_path).get("modules_run", [])
        requested = [r["module"] for r in prior_run_log if r["status"] == "error"]
        if not requested:
            print(f"no failed modules in {run_log_path} -- nothing to retry")
            return 0
    else:
        requested = args.modules.split(",") if args.modules else list(MODULES)
        unknown = set(requested) - set(MODULES)
        if unknown:
            print(f"unknown module(s): {unknown}. Available: {MODULES}", file=sys.stderr)
            return 2
        if args.skip_slow:
            requested = [m for m in requested if m not in SLOW_MODULES]

    print(f"target: {target} ({'portfolio of ' + str(len(repos)) + ' repos' if is_portfolio else 'single repo'})")
    print(f"output: {out_dir}")
    print(f"modules: {requested}")

    # retrying keeps every OTHER module's result from the prior run intact --
    # only the modules actually being retried get their run_log.json entry
    # replaced with this attempt's fresh outcome, success or another failure.
    run_log = [r for r in prior_run_log if r["module"] not in requested]
    for name in requested:
        print(f"--- running {name} ---", flush=True)
        result = run_module(name, repos, target, out_dir, tmp_dir)
        run_log.append(result)
        status_line = f"{name}: {result['status']} ({result['elapsed_s']}s)"
        if result["status"] == "error":
            status_line += f" -- {result['error']}"
        print(status_line, flush=True)

    write_json(out_dir / "run_log.json", {
        "target": str(target), "repo_count": len(repos), "modules_run": run_log,
    })
    failures = [r for r in run_log if r["status"] == "error"]
    print(f"\n{len(run_log) - len(failures)}/{len(run_log)} modules completed. Raw output in {out_dir}")
    if failures:
        print(f"FAILED modules (see run_log.json for tracebacks): {[f['module'] for f in failures]}")

    from .reporting.report import render_report
    report_path = render_report(out_dir, target.resolve().name)
    print(f"report: {report_path}")
    return 1 if failures else 0


def cmd_list_modules(_args: argparse.Namespace) -> int:
    for m in MODULES:
        print(f"{m}{' (slow)' if m in SLOW_MODULES else ''}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .reporting.report import render_report
    out_dir = Path(args.out_dir)
    report_path = render_report(out_dir, out_dir.name)
    print(f"report: {report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo Analyser: multi-dimensional repo/portfolio analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze a single repo or a directory of repos")
    p_analyze.add_argument("target", help="Path to a git repo, or a directory of git repos")
    p_analyze.add_argument("--out", help="Output directory (default: analyses/<target-name>)")
    p_analyze.add_argument("--modules", help=f"Comma-separated subset of: {','.join(MODULES)}")
    p_analyze.add_argument("--skip-slow", action="store_true",
                            help=f"Skip slow modules ({','.join(sorted(SLOW_MODULES))})")
    p_analyze.add_argument("--retry-failed", action="store_true",
                            help="Re-run only the modules that failed in --out's existing run_log.json "
                                 "(ignores --modules/--skip-slow; requires a prior run in --out)")
    p_analyze.set_defaults(func=cmd_analyze)

    p_list = sub.add_parser("list-modules", help="List available analysis modules")
    p_list.set_defaults(func=cmd_list_modules)

    p_report = sub.add_parser("report", help="Regenerate REPORT.md from an existing output directory")
    p_report.add_argument("out_dir", help="Output directory from a previous `analyze` run")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
