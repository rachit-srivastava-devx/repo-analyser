from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx

from repo_analyser.graph.knowledge_graph import (
    _read_import_edges,
    build_graph,
    export_graphml,
    graph_stats,
    run_knowledge_graph,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class TestBuildGraph:
    def test_missing_csvs_produce_an_empty_but_valid_graph(self, tmp_path: Path) -> None:
        G = build_graph(tmp_path)
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_inventory_rows_become_repo_nodes(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "inventory.csv", [
            {"repo": "svc-a", "total_commits": "42", "tier": "active"},
            {"repo": "svc-b", "total_commits": "7", "tier": "dormant"},
        ])
        G = build_graph(tmp_path)
        assert set(G.nodes()) == {"repo:svc-a", "repo:svc-b"}
        assert G.nodes["repo:svc-a"]["total_commits"] == 42
        assert G.nodes["repo:svc-a"]["tier"] == "active"

    def test_exact_duplicates_produce_bidirectional_duplicate_of_edges(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "exact_duplicate_files.csv", [
            {"path": "src/util.ts", "repos": "svc-a;svc-b;svc-c"},
        ])
        G = build_graph(tmp_path)
        # 3 repos sharing one file -> C(3,2) = 3 pairs, each bidirectional
        dup_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("type") == "DUPLICATE_OF"]
        assert len(dup_edges) == 6
        assert G.get_edge_data("repo:svc-a", "repo:svc-b", key="DUPLICATE_OF")["weight"] == 1

    def test_duplicate_weight_accumulates_across_multiple_shared_files(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "exact_duplicate_files.csv", [
            {"path": "a.ts", "repos": "svc-a;svc-b"},
            {"path": "b.ts", "repos": "svc-a;svc-b"},
        ])
        G = build_graph(tmp_path)
        assert G.get_edge_data("repo:svc-a", "repo:svc-b", key="DUPLICATE_OF")["weight"] == 2

    def test_shares_package_respects_the_five_package_floor(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        for name, deps in [("svc-a", ["p1", "p2", "p3", "p4"]), ("svc-b", ["p1", "p2", "p3", "p4"])]:
            repo_dir = portfolio / name
            repo_dir.mkdir(parents=True)
            (repo_dir / "package.json").write_text(json.dumps({"dependencies": {d: "1.0.0" for d in deps}}))
        G = build_graph(tmp_path, portfolio_root=portfolio)
        # only 4 shared deps -- below the >=5 floor -- so no SHARES_PACKAGE edge
        share_edges = [e for e in G.edges(data=True) if e[2].get("type") == "SHARES_PACKAGE"]
        assert share_edges == []

    def test_shares_package_fires_at_five_shared_deps(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        deps = ["p1", "p2", "p3", "p4", "p5"]
        for name in ["svc-a", "svc-b"]:
            repo_dir = portfolio / name
            repo_dir.mkdir(parents=True)
            (repo_dir / "package.json").write_text(json.dumps({"dependencies": {d: "1.0.0" for d in deps}}))
        G = build_graph(tmp_path, portfolio_root=portfolio)
        edge = G.get_edge_data("repo:svc-a", "repo:svc-b", key="SHARES_PACKAGE")
        assert edge["weight"] == 5

    def test_malformed_package_json_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        repo_dir = portfolio / "svc-a"
        repo_dir.mkdir(parents=True)
        (repo_dir / "package.json").write_text("{not valid json")
        G = build_graph(tmp_path, portfolio_root=portfolio)
        assert G.number_of_nodes() == 0  # no crash, just nothing added for this repo

    def test_coupled_with_creates_file_nodes_scoped_by_repo(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "churn_coupling.csv", [
            {"repo": "svc-a", "entity": "a.ts", "coupled": "b.ts", "degree": "5"},
        ])
        G = build_graph(tmp_path)
        assert "file:svc-a/a.ts" in G.nodes()
        assert "file:svc-a/b.ts" in G.nodes()
        edge = G.get_edge_data("file:svc-a/a.ts", "file:svc-a/b.ts", key="COUPLED_WITH")
        assert edge["weight"] == 5

    def test_no_portfolio_root_skips_shares_package_without_crashing(self, tmp_path: Path) -> None:
        G = build_graph(tmp_path, portfolio_root=None)
        assert G.number_of_nodes() == 0

    def test_shares_package_generalizes_to_python_via_requirements_txt(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        deps = "requests==2.31.0\nflask>=2.0\nnumpy\npandas~=2.0\npytest!=7.0\n"
        for name in ["svc-a", "svc-b"]:
            repo_dir = portfolio / name
            repo_dir.mkdir(parents=True)
            (repo_dir / "requirements.txt").write_text(deps)
            (repo_dir / "main.py").write_text("x = 1\n")
        G = build_graph(tmp_path, portfolio_root=portfolio)
        edge = G.get_edge_data("repo:svc-a", "repo:svc-b", key="SHARES_PACKAGE")
        assert edge["weight"] == 5

    def test_shares_package_generalizes_to_go_via_go_mod(self, tmp_path: Path) -> None:
        portfolio = tmp_path / "portfolio"
        go_mod = (
            "module example.com/svc\n\ngo 1.21\n\nrequire (\n"
            "\tgithub.com/a/one v1.0.0\n\tgithub.com/a/two v1.0.0\n"
            "\tgithub.com/a/three v1.0.0\n\tgithub.com/a/four v1.0.0\n"
            "\tgithub.com/a/five v1.0.0\n)\n"
        )
        for name in ["svc-a", "svc-b"]:
            repo_dir = portfolio / name
            repo_dir.mkdir(parents=True)
            (repo_dir / "go.mod").write_text(go_mod)
            (repo_dir / "main.go").write_text("package main\n")
        G = build_graph(tmp_path, portfolio_root=portfolio)
        edge = G.get_edge_data("repo:svc-a", "repo:svc-b", key="SHARES_PACKAGE")
        assert edge["weight"] == 5

    def test_shares_package_does_not_cross_language_pairs(self, tmp_path: Path) -> None:
        # a same-named package in two different ecosystems (npm's "requests"
        # vs PyPI's "requests") is not a real shared dependency -- pairs
        # are only ever compared within the same detected language.
        portfolio = tmp_path / "portfolio"
        same_names = ["p1", "p2", "p3", "p4", "p5"]
        js_repo = portfolio / "js-repo"
        js_repo.mkdir(parents=True)
        (js_repo / "package.json").write_text(json.dumps({"dependencies": {d: "1.0.0" for d in same_names}}))
        py_repo = portfolio / "py-repo"
        py_repo.mkdir(parents=True)
        (py_repo / "requirements.txt").write_text("\n".join(same_names))
        (py_repo / "main.py").write_text("x = 1\n")
        G = build_graph(tmp_path, portfolio_root=portfolio)
        share_edges = [e for e in G.edges(data=True) if e[2].get("type") == "SHARES_PACKAGE"]
        assert share_edges == []


class TestReadImportEdges:
    def test_python_go_shaped_raw_passes_through(self) -> None:
        raw = {"nodes": ["a", "b", "c"], "edges": [["a", "b"], ["b", "c"]]}
        assert _read_import_edges(raw) == [("a", "b"), ("b", "c")]

    def test_js_shaped_raw_extracts_internal_edges_only(self) -> None:
        # dependency-cruiser's real `resolved` paths for a repo's own code
        # start with "./" or "/" -- see core.lang.is_internal_js_module,
        # grounded against depgraph.py's own _aggregate(), not guessed.
        raw = {"modules": [{
            "source": "./src/a.ts",
            "dependencies": [
                {"resolved": "./src/b.ts"},
                {"resolved": "node_modules/lodash/index.js"},
                {"resolved": "@some/external-pkg"},
            ],
        }]}
        assert _read_import_edges(raw) == [("./src/a.ts", "./src/b.ts")]

    def test_js_shaped_raw_skips_node_modules_sourced_modules(self) -> None:
        raw = {"modules": [{"source": "node_modules/pkg/index.js", "dependencies": [{"resolved": "src/a.ts"}]}]}
        assert _read_import_edges(raw) == []

    def test_empty_raw_returns_empty(self) -> None:
        assert _read_import_edges({}) == []


class TestBuildGraphImportsEdge:
    def test_imports_edge_from_python_shaped_depgraph_raw(self, tmp_path: Path) -> None:
        raw_dir = tmp_path / "depgraph_raw"
        raw_dir.mkdir()
        (raw_dir / "svc-a.json").write_text(json.dumps({"nodes": ["a", "b"], "edges": [["a", "b"]]}))
        G = build_graph(tmp_path)
        assert "file:svc-a/a" in G.nodes()
        assert "file:svc-a/b" in G.nodes()
        edge = G.get_edge_data("file:svc-a/a", "file:svc-a/b", key="IMPORTS")
        assert edge["weight"] == 1

    def test_imports_edge_from_js_shaped_depgraph_raw_filters_external(self, tmp_path: Path) -> None:
        raw_dir = tmp_path / "depgraph_raw"
        raw_dir.mkdir()
        raw = {"modules": [{
            "source": "./src/a.ts",
            "dependencies": [{"resolved": "./src/b.ts"}, {"resolved": "node_modules/lodash/index.js"}],
        }]}
        (raw_dir / "svc-a.json").write_text(json.dumps(raw))
        G = build_graph(tmp_path)
        assert G.get_edge_data("file:svc-a/./src/a.ts", "file:svc-a/./src/b.ts", key="IMPORTS") is not None
        assert "file:svc-a/node_modules/lodash/index.js" not in G.nodes()

    def test_no_depgraph_raw_dir_skips_imports_without_crashing(self, tmp_path: Path) -> None:
        G = build_graph(tmp_path)
        assert G.number_of_nodes() == 0

    def test_malformed_depgraph_raw_json_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        raw_dir = tmp_path / "depgraph_raw"
        raw_dir.mkdir()
        (raw_dir / "svc-a.json").write_text("{not valid json")
        G = build_graph(tmp_path)
        assert G.number_of_nodes() == 0


class TestExportGraphml:
    def test_roundtrips_through_a_real_file(self, tmp_path: Path) -> None:
        G = nx.MultiDiGraph()
        G.add_node("repo:a", type="repo", total_commits=10, tier="active")
        G.add_edge("repo:a", "repo:b", key="DUPLICATE_OF", type="DUPLICATE_OF", weight=3)
        out_path = export_graphml(G, tmp_path / "sub" / "graph.graphml")
        assert out_path.exists()
        reloaded = nx.read_graphml(out_path)
        assert reloaded.number_of_nodes() == 2
        assert reloaded.number_of_edges() == 1


class TestGraphStats:
    def test_empty_graph(self) -> None:
        stats = graph_stats(nx.MultiDiGraph())
        assert stats["total_nodes"] == 0
        assert stats["top_connected_repos"] == []

    def test_counts_edge_types_and_ranks_by_degree(self) -> None:
        G = nx.MultiDiGraph()
        G.add_node("repo:a", type="repo")
        G.add_node("repo:b", type="repo")
        G.add_node("repo:c", type="repo")
        G.add_edge("repo:a", "repo:b", key="DUPLICATE_OF", type="DUPLICATE_OF", weight=1)
        G.add_edge("repo:b", "repo:a", key="DUPLICATE_OF", type="DUPLICATE_OF", weight=1)
        G.add_edge("repo:a", "repo:c", key="SHARES_PACKAGE", type="SHARES_PACKAGE", weight=5)
        stats = graph_stats(G)
        assert stats["edge_type_counts"] == {"DUPLICATE_OF": 2, "SHARES_PACKAGE": 1}
        assert stats["top_connected_repos"][0]["repo"] == "a"  # degree 3 (2 dup + 1 share)

    def test_file_nodes_counted_separately_from_repo_nodes(self) -> None:
        G = nx.MultiDiGraph()
        G.add_node("repo:a", type="repo")
        G.add_node("file:a/x.ts", type="file")
        stats = graph_stats(G)
        assert stats["repo_nodes"] == 1
        assert stats["file_nodes"] == 1


class TestRunKnowledgeGraph:
    def test_writes_graphml_and_stats_json(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        _write_csv(data_dir / "inventory.csv", [{"repo": "svc-a", "total_commits": "1", "tier": "active"}])
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        graphml_path = run_knowledge_graph(data_dir, tmp_path / "nonexistent_portfolio", out_dir)
        assert graphml_path.exists()
        stats = json.loads((out_dir / "knowledge_graph_stats.json").read_text())
        assert stats["total_nodes"] == 1
