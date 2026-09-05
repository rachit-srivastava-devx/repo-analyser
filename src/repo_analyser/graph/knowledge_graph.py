"""A real, queryable, portfolio-wide knowledge graph -- not a paragraph
describing one. Assembles every relationship this tool has already
computed (exact duplication, shared dependencies, within-repo temporal
coupling, within-repo import graphs) into one networkx MultiDiGraph and
exports it as GraphML: a standard, tool-interoperable format any graph
tool can load (Gephi, yEd, Neo4j's neo4j-admin import, igraph, networkx
itself) -- not a bespoke format only this tool understands.

Node types: repo, file (only files involved in a cross-repo relationship
-- see "Honest limitations" in the rendered report for why full per-file
nodes aren't included at portfolio scale).
Edge types:
  DUPLICATE_OF   repo<->repo, weight = count of byte-identical files shared
                 (from exact_duplicates.py's output -- sha256, not a guess)
  SHARES_PACKAGE repo<->repo, weight = count of shared same-ecosystem
                 dependencies (npm/pip/go -- see PORTFOLIO_DEP_READERS)
  COUPLED_WITH   file<->file within one repo, weight = co-change degree
                 (from code-maat's temporal coupling -- churn.py's output)
  IMPORTS        file<->file within one repo, from depgraph.py's own
                 already-computed per-repo import graph (depgraph_raw/*.json)

This module reads only files already written by other modules -- it does
not re-scan any repo, with one narrow, pre-existing exception: SHARES_PACKAGE
reads each repo's own dependency manifest directly (cheap, static-file
reads only -- see PORTFOLIO_DEP_READERS) rather than depending on another
module's summarized output.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx

from ..core.lang import is_internal_js_module


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _npm_deps(repo: Path) -> set[str]:
    pj = repo / "package.json"
    if not pj.exists():
        return set()
    try:
        d = json.loads(pj.read_text())
    except json.JSONDecodeError:
        return set()
    return set(d.get("dependencies", {}).keys())


_REQUIREMENT_SPECIFIER_RE = re.compile(r"[=<>!~\[; ]")


def _python_deps(repo: Path) -> set[str]:
    # requirements.txt only -- pyproject.toml's [project.dependencies] /
    # [tool.poetry.dependencies] is a real, common alternative not covered
    # here (would need a TOML parser); stated honestly rather than
    # silently missed.
    req = repo / "requirements.txt"
    if not req.exists():
        return set()
    deps = set()
    for line in req.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = _REQUIREMENT_SPECIFIER_RE.split(line, 1)[0].strip()
        if name:
            deps.add(name.lower())
    return deps


def _go_deps(repo: Path) -> set[str]:
    mod = repo / "go.mod"
    if not mod.exists():
        return set()
    deps = set()
    in_require_block = False
    for line in mod.read_text().splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block:
            if line.startswith(")"):
                in_require_block = False
                continue
            parts = line.split()
            if parts:
                deps.add(parts[0])
        elif line.startswith("require "):
            parts = line.split()
            if len(parts) >= 2:
                deps.add(parts[1])
    return deps


# Which manifest to read per detected language -- generalizes SHARES_PACKAGE
# past its original npm-only form (docs/METHODOLOGY.md #32) to the same
# three languages depgraph.py/testquality.py/mutation.py already support.
PORTFOLIO_DEP_READERS = {"javascript": _npm_deps, "python": _python_deps, "go": _go_deps}


def _read_import_edges(raw: dict) -> list[tuple[str, str]]:
    """Normalizes depgraph.py's two on-disk raw shapes (depgraph_raw/*.json)
    into a plain (source, target) edge list. Python/Go already write
    {"nodes": [...], "edges": [[src, dst], ...]} with only internal edges
    included (see depgraph.py's own _analyze_python_repo/_analyze_go_repo).
    JS writes dependency-cruiser's own raw JSON
    ({"modules": [{"source": ..., "dependencies": [...]}]}), which still
    includes node_modules/external noise that must be filtered the same
    way depgraph.py's own _aggregate() does -- via the shared
    core.lang.is_internal_js_module, not a re-guessed rule."""
    if "edges" in raw:
        return [(e[0], e[1]) for e in raw["edges"]]
    edges = []
    for m in raw.get("modules", []):
        if "node_modules" in m.get("source", ""):
            continue
        for d in m.get("dependencies", []):
            resolved = d.get("resolved", "")
            if is_internal_js_module(resolved):
                edges.append((m["source"], resolved))
    return edges


def build_graph(data_dir: Path, portfolio_root: Path | None = None) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()

    inv = _read_csv(data_dir / "inventory.csv")
    for r in inv:
        G.add_node(f"repo:{r['repo']}", type="repo", total_commits=int(r["total_commits"]),
                   tier=r["tier"])

    # DUPLICATE_OF: repo<->repo, weighted by shared byte-identical file count
    exact = _read_csv(data_dir / "exact_duplicate_files.csv")
    dup_weight: dict[tuple[str, str], int] = defaultdict(int)
    for row in exact:
        repos = [r for r in row["repos"].split(";") if r]
        for a, b in combinations(sorted(repos), 2):
            dup_weight[(a, b)] += 1
    for (a, b), w in dup_weight.items():
        G.add_edge(f"repo:{a}", f"repo:{b}", key="DUPLICATE_OF", type="DUPLICATE_OF", weight=w)
        G.add_edge(f"repo:{b}", f"repo:{a}", key="DUPLICATE_OF", type="DUPLICATE_OF", weight=w)

    # SHARES_PACKAGE: repo<->repo, weighted by shared same-ecosystem
    # dependency count (recomputed fresh from each repo's own manifest --
    # cheap, and keeps this module honest about its own inputs rather than
    # depending on shared_deps.json's top-N-only summary). Which manifest a
    # repo has, not detect_repo_language's dominant-file-extension guess,
    # decides its ecosystem here -- a repo can have a manifest (and thus a
    # real ecosystem) without yet having enough of that language's own
    # source files to win the file-count vote (e.g. a fresh test fixture,
    # or a repo genuinely dominated by another language). Pairs are only
    # ever compared within the SAME ecosystem -- a same-named package in
    # two different ecosystems (e.g. npm's and PyPI's own unrelated
    # "requests") is not a real shared dependency, and the >=5 floor below
    # exists precisely to make that kind of coincidence vanishingly
    # unlikely even before this check, but comparing only same-ecosystem
    # pairs rules it out by construction instead.
    if portfolio_root and portfolio_root.exists():
        repo_deps: dict[str, tuple[str, set[str]]] = {}
        for repo in sorted(portfolio_root.iterdir()):
            if not repo.is_dir():
                continue
            for ecosystem, reader in PORTFOLIO_DEP_READERS.items():
                deps = reader(repo)
                if deps:
                    repo_deps[repo.name] = (ecosystem, deps)
                    break
        for a, b in combinations(sorted(repo_deps), 2):
            eco_a, deps_a = repo_deps[a]
            eco_b, deps_b = repo_deps[b]
            if eco_a != eco_b:
                continue
            shared = deps_a & deps_b
            if len(shared) >= 5:  # floor: every repo shares *some* common package; only report real overlap
                G.add_edge(f"repo:{a}", f"repo:{b}", key="SHARES_PACKAGE", type="SHARES_PACKAGE",
                           weight=len(shared), packages=";".join(sorted(shared))[:500])
                G.add_edge(f"repo:{b}", f"repo:{a}", key="SHARES_PACKAGE", type="SHARES_PACKAGE",
                           weight=len(shared), packages=";".join(sorted(shared))[:500])

    # COUPLED_WITH: file<->file, within one repo (code-maat temporal coupling)
    coupling = _read_csv(data_dir / "churn_coupling.csv")
    for row in coupling:
        repo = row["repo"]
        a, b = f"file:{repo}/{row['entity']}", f"file:{repo}/{row['coupled']}"
        G.add_node(a, type="file", repo=repo)
        G.add_node(b, type="file", repo=repo)
        G.add_edge(a, b, key="COUPLED_WITH", type="COUPLED_WITH", weight=int(row["degree"]))

    # IMPORTS: file<->file, within one repo, from depgraph.py's own
    # already-computed per-repo import graphs (depgraph_raw/*.json) --
    # zero new scanning cost, matching this module's own stated "reads
    # only files already written by other modules" design
    # (docs/METHODOLOGY.md #32).
    depgraph_raw_dir = data_dir / "depgraph_raw"
    if depgraph_raw_dir.is_dir():
        for repo_json in sorted(depgraph_raw_dir.glob("*.json")):
            repo_name = repo_json.stem
            try:
                raw = json.loads(repo_json.read_text())
            except json.JSONDecodeError:
                continue
            for src, dst in _read_import_edges(raw):
                a, b = f"file:{repo_name}/{src}", f"file:{repo_name}/{dst}"
                G.add_node(a, type="file", repo=repo_name)
                G.add_node(b, type="file", repo=repo_name)
                G.add_edge(a, b, key="IMPORTS", type="IMPORTS", weight=1)

    return G


def export_graphml(G: nx.MultiDiGraph, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, out_path)
    return out_path


def graph_stats(G: nx.MultiDiGraph) -> dict:
    edge_type_counts: dict[str, int] = defaultdict(int)
    for _, _, data in G.edges(data=True):
        edge_type_counts[data.get("type", "?")] += 1
    repo_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "repo"]
    file_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "file"]
    degree = dict(G.degree(repo_nodes))
    top_connected = sorted(degree.items(), key=lambda kv: -kv[1])[:10]
    return {
        "total_nodes": G.number_of_nodes(), "total_edges": G.number_of_edges(),
        "repo_nodes": len(repo_nodes), "file_nodes": len(file_nodes),
        "edge_type_counts": dict(edge_type_counts),
        "top_connected_repos": [{"repo": n.replace("repo:", ""), "degree": d} for n, d in top_connected],
    }


def run_knowledge_graph(data_dir: Path, portfolio_root: Path, out_dir: Path) -> Path:
    G = build_graph(data_dir, portfolio_root)
    graphml_path = export_graphml(G, out_dir / "knowledge_graph.graphml")
    stats = graph_stats(G)
    (out_dir / "knowledge_graph_stats.json").write_text(json.dumps(stats, indent=2))
    return graphml_path
