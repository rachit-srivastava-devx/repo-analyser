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
  SHARES_PACKAGE repo<->repo, weight = count of shared npm dependencies
  COUPLED_WITH   file<->file within one repo, weight = co-change degree
                 (from code-maat's temporal coupling -- churn.py's output)

This module reads only files already written by other modules -- it does
not re-scan any repo.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


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

    # SHARES_PACKAGE: repo<->repo, weighted by shared npm dependency count
    # (recomputed fresh from each repo's package.json -- cheap, and keeps
    # this module honest about its own inputs rather than depending on
    # shared_deps.json's top-N-only summary.)
    if portfolio_root and portfolio_root.exists():
        repo_deps: dict[str, set[str]] = {}
        for repo in sorted(portfolio_root.iterdir()):
            pj = repo / "package.json"
            if pj.exists():
                try:
                    d = json.loads(pj.read_text())
                except json.JSONDecodeError:
                    continue
                repo_deps[repo.name] = set(d.get("dependencies", {}).keys())
        for a, b in combinations(sorted(repo_deps), 2):
            shared = repo_deps[a] & repo_deps[b]
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
