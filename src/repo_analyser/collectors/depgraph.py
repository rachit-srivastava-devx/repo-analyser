"""Within-repo import dependency graph. JavaScript/TypeScript via
dependency-cruiser (needs `node_modules` present -- its TypeScript
resolution silently returns zero modules without it, which is worse than
an error, so a missing node_modules is treated as a precondition failure,
not a valid empty result). Python via a direct `ast`-based import-graph
builder (no external tool needed). Go via `go list -json` (needs `go.mod`
and, ideally, a populated module cache).

Honesty note: the Python and Go paths were built and smoke-tested against
small synthetic fixtures (see tests/), not against a real large-scale
polyglot codebase -- none was available in the portfolio this tool was
first built against (100% JS/TS). Expect rough edges on unusual project
layouts (namespace packages, build-tag-gated Go files, etc.) that a
JS/TS-only validation pass would not have caught.
"""
from __future__ import annotations

import ast
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import networkx as nx

from ..core.lang import DEPGRAPH_SUPPORTED, EXCLUDE_DIR_PARTS, detect_repo_language, is_internal_js_module
from ..core.util import run, run_concurrent, write_csv, write_json


@dataclass
class RepoDepGraph:
    repo: str
    total_modules: int
    total_dependencies: int
    circular_count: int
    orphan_count: int
    top_in_degree_module: str
    top_in_degree: int
    skipped_reason: str = ""


SOURCE_EXTS = (".ts", ".tsx", ".js", ".jsx")


def _source_files(target: Path) -> list[str]:
    files = []
    for p in target.rglob("*"):
        if p.suffix in SOURCE_EXTS and p.is_file() and not any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            files.append(str(p))
    return files


def analyze_repo(repo: Path, out_dir: Path) -> RepoDepGraph:
    lang = detect_repo_language(repo)
    if lang == "python":
        return _analyze_python_repo(repo, out_dir)
    if lang == "go":
        return _analyze_go_repo(repo, out_dir)
    if lang != "javascript":
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0,
                             skipped_reason=f"language '{lang}' not supported by depgraph "
                                            f"(supported: {sorted(DEPGRAPH_SUPPORTED)})")
    return _analyze_js_repo(repo, out_dir)


def _analyze_js_repo(repo: Path, out_dir: Path) -> RepoDepGraph:
    if not (repo / "node_modules").is_dir():
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0, skipped_reason="no node_modules (npm install failed)")

    ts_config = repo / "tsconfig.json"
    src_dir = repo / "src"
    target = src_dir if src_dir.is_dir() else repo
    # NOTE: dependency-cruiser 18.2.0 silently returns 0 modules when given a
    # directory positional arg in this setup (confirmed by direct comparison:
    # 0 modules for the dir form vs 7585 for an explicit file list on the
    # same repo) -- pass an explicit file list instead of relying on its
    # internal directory recursion.
    files = _source_files(target)
    if not files:
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0, skipped_reason=f"no source files under {target}")
    # exact version pin (docs/METHODOLOGY.md #33): this module's own
    # "silently returns 0 modules for a dir arg" quirk a few lines above
    # was diagnosed and grounded against 18.2.0 specifically -- an
    # unpinned `npx dependency-cruiser` always resolves whatever's latest
    # (or stale-cached), which is exactly the "unpinned CLI tool silently
    # changes behavior" class of bug that hit mutmut (docs/METHODOLOGY.md
    # #24) before it was pinned exact there too.
    cmd = ["npx", "--yes", "dependency-cruiser@18.2.0", *[str(Path(f).relative_to(repo)) for f in files],
           "--no-config", "--output-type", "json"]
    if ts_config.exists():
        cmd += ["--ts-config", "tsconfig.json"]
    # npx has no --ignore-scripts of its own (that's an `npm install` flag);
    # npm_config_ignore_scripts is the documented env-var equivalent npx
    # itself respects for its own install-if-missing step. Same rationale
    # as mutation.py's Stryker install: dependency-cruiser is a tool-chosen
    # trusted package, installed inside whatever arbitrary target repo this
    # tool is pointed at -- see docs/ARCHITECTURE.md "Security model".
    res = run(cmd, cwd=repo, check=False, timeout=180, extra_env={"npm_config_ignore_scripts": "true"})
    if not res.stdout.strip():
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0,
                             skipped_reason=f"dependency-cruiser produced no output: {res.stderr[:300]}")
    data = json.loads(res.stdout)
    (out_dir / "depgraph_raw").mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "depgraph_raw" / f"{repo.name}.json", data)
    return _aggregate(data, repo.name)


def _aggregate(data: dict, repo_name: str) -> RepoDepGraph:
    # dependency-cruiser, given a file list, recursively follows imports
    # *into* node_modules and reports third-party internals as modules in
    # their own right (e.g. a package's own circular requires show up as
    # "circular" edges in this repo's graph). Restricting to modules whose
    # own source is NOT under node_modules is what makes total_modules,
    # circular_count, and orphan_count reflect the analyzed repo's own code
    # rather than its dependencies' internals -- confirmed by inspecting a
    # sample "circular" edge that turned out to be entirely inside the `bl`
    # package's own readable-stream shim, unrelated to any app code.
    all_modules = data.get("modules", [])
    modules = [m for m in all_modules if "node_modules" not in m.get("source", "")]

    in_degree: dict[str, int] = defaultdict(int)
    total_deps = 0
    circular = 0
    orphans = 0
    for m in modules:
        deps = [d for d in m.get("dependencies", []) if "node_modules" not in d.get("resolved", "")]
        total_deps += len(deps)
        if m.get("orphan"):
            orphans += 1
        for d in deps:
            resolved = d.get("resolved", "")
            if d.get("circular"):
                circular += 1
            if is_internal_js_module(resolved):
                in_degree[resolved] += 1

    top_module, top_count = max(in_degree.items(), key=lambda kv: kv[1]) if in_degree else ("", 0)
    return RepoDepGraph(
        repo=repo_name, total_modules=len(modules), total_dependencies=total_deps,
        circular_count=circular, orphan_count=orphans,
        top_in_degree_module=top_module, top_in_degree=top_count,
    )


# core.lang.EXCLUDE_DIR_PARTS plus "site-packages", which only matters for
# an installed-editable Python environment sitting inside the repo tree.
PY_EXCLUDE = EXCLUDE_DIR_PARTS | {"site-packages"}


def _py_module_name(repo: Path, file: Path) -> str:
    rel = file.relative_to(repo).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join(parts)


def _py_imports(file: Path) -> list[list[str]]:
    """Returns one candidate-list per logical import statement. For
    `from X import Y`, Y might be a submodule (real target "X.Y") or an
    attribute/function/class defined in X's __init__ (real target "X") --
    both candidates are returned, most-specific first, so the caller can
    resolve against known local module names and prefer the specific match
    without double-counting one import as two edges. Losing this
    distinction was a real bug: flattening both candidates into one list
    made every `from pkg import b`-style import resolve only to "pkg",
    collapsing every submodule's real import target onto its package's
    __init__ and producing a wrong in-degree ranking -- caught by
    smoke-testing against a fixture with a known-correct expected graph."""
    try:
        tree = ast.parse(file.read_text(errors="ignore"), filename=str(file))
    except SyntaxError:
        return []
    out: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append([a.name])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                out.append([f"{node.module}.{alias.name}", node.module])
    return out


def _analyze_python_repo(repo: Path, out_dir: Path) -> RepoDepGraph:
    """Best-effort internal import graph: every local module's dotted name
    is derived from its file path, and an import is "internal" if it
    exactly matches, or is a dotted-prefix of, some local module name.
    This under-counts internal edges for src-layout projects where the
    import path doesn't match the file path 1:1 (e.g. an installed
    editable package) -- a real, stated limitation, not a silent gap."""
    py_files = [p for p in repo.rglob("*.py") if not any(part in PY_EXCLUDE for part in p.parts)]
    if not py_files:
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0, skipped_reason="no .py files found")

    module_names = {_py_module_name(repo, f) for f in py_files}
    G = nx.DiGraph()
    for f in py_files:
        G.add_node(_py_module_name(repo, f))

    total_deps = 0
    for f in py_files:
        src_mod = _py_module_name(repo, f)
        for candidates in _py_imports(f):
            # exact match only, most-specific candidate first -- a prefix-based
            # fallback here was tried and dropped: it matched non-deterministically
            # depending on set iteration order (e.g. "pkg" could resolve to either
            # "pkg" or "pkg.b" depending on hash order), which is worse than a
            # slightly narrower but deterministic match.
            match = next((c for c in candidates if c in module_names), None)
            if match and match != src_mod:
                G.add_edge(src_mod, match)
                total_deps += 1

    in_degree = dict(G.in_degree())
    top_module, top_count = max(in_degree.items(), key=lambda kv: kv[1]) if in_degree else ("", 0)
    try:
        circular = sum(1 for _ in nx.simple_cycles(G))
    except Exception:  # noqa: BLE001 -- cycle detection is best-effort on large/odd graphs
        circular = -1  # signals "not computed", not "zero found"
    orphans = sum(1 for n in G.nodes() if G.in_degree(n) == 0 and G.out_degree(n) == 0)

    graph_json = {"nodes": list(G.nodes()), "edges": list(G.edges())}
    (out_dir / "depgraph_raw").mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "depgraph_raw" / f"{repo.name}.json", graph_json)

    return RepoDepGraph(
        repo=repo.name, total_modules=G.number_of_nodes(), total_dependencies=total_deps,
        circular_count=circular, orphan_count=orphans,
        top_in_degree_module=top_module, top_in_degree=top_count,
    )


def _analyze_go_repo(repo: Path, out_dir: Path) -> RepoDepGraph:
    go_mod = repo / "go.mod"
    if not go_mod.exists():
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0, skipped_reason="no go.mod found")
    module_line = next((line for line in go_mod.read_text().splitlines() if line.startswith("module ")), None)
    if not module_line:
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0, skipped_reason="go.mod has no module directive")
    module_path = module_line.split()[1].strip()

    res = run(["go", "list", "-json", "./..."], cwd=repo, check=False, timeout=120)
    if res.returncode != 0 or not res.stdout.strip():
        return RepoDepGraph(repo.name, 0, 0, 0, 0, "", 0,
                             skipped_reason=f"`go list` failed (missing deps or network needed?): {res.stderr[:300]}")

    # `go list -json ./...` emits one JSON object per package, concatenated
    # (not a JSON array) -- decode with a streaming raw_decode loop.
    decoder = json.JSONDecoder()
    text = res.stdout
    idx = 0
    packages = []
    while idx < len(text):
        text_from = text[idx:].lstrip()
        if not text_from:
            break
        idx += len(text[idx:]) - len(text_from)
        obj, end = decoder.raw_decode(text, idx)
        packages.append(obj)
        idx = end

    G = nx.DiGraph()
    total_deps = 0
    for pkg in packages:
        src = pkg.get("ImportPath", "")
        G.add_node(src)
        for imp in pkg.get("Imports", []) or []:
            if imp.startswith(module_path):
                G.add_edge(src, imp)
                total_deps += 1

    in_degree = dict(G.in_degree())
    top_module, top_count = max(in_degree.items(), key=lambda kv: kv[1]) if in_degree else ("", 0)
    try:
        circular = sum(1 for _ in nx.simple_cycles(G))
    except Exception:  # noqa: BLE001
        circular = -1
    orphans = sum(1 for n in G.nodes() if G.in_degree(n) == 0 and G.out_degree(n) == 0)

    graph_json = {"nodes": list(G.nodes()), "edges": list(G.edges())}
    (out_dir / "depgraph_raw").mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "depgraph_raw" / f"{repo.name}.json", graph_json)

    return RepoDepGraph(
        repo=repo.name, total_modules=G.number_of_nodes(), total_dependencies=total_deps,
        circular_count=circular, orphan_count=orphans,
        top_in_degree_module=top_module, top_in_degree=top_count,
    )


def run_depgraph(repos: list[Path], out_dir: Path) -> Path:
    # each repo's own import-graph build is one I/O-bound subprocess call
    # (or, for Python, pure local computation) -- see
    # core.util.run_concurrent's docstring. Each repo writes to its own
    # depgraph_raw/<repo>.json, so there's no shared mutable state here.
    rows = [asdict(r) for r in run_concurrent(repos, lambda r: analyze_repo(r, out_dir))]
    out_path = out_dir / "depgraph_summary.csv"
    write_csv(out_path, rows, fieldnames=RepoDepGraph)
    return out_path
