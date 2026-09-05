# RAG / Vector-Store Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| docker-compose or deployment config referencing Qdrant/Weaviate/Milvus/Chroma/pgvector, or a llama-index/langchain dependency paired with an ingest/chunking script | `grep -riE "qdrant|weaviate|milvus|chromadb|pgvector" docker-compose.yml requirements.txt package.json` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Chunking-strategy documentation & versioning** | the chosen chunk size, overlap, and splitting method are written down and git-versioned like any other config, since silently changing any of the three invalidates every embedding already sitting in the index. | `ChunkViz`, `adr-tools`, `MADR template` |
| **PII scrubbing before embedding** | names, IDs, secrets, and other sensitive fields are detected and redacted or tokenized before a document is embedded, since a vector store is an easy-to-overlook place for PII to leak back out through retrieval. | `Microsoft Presidio`, `piicatcher` |
| **Embedding-model version pinning** | the exact embedding model and version behind every vector is recorded, and a full corpus re-embed is triggered and tracked whenever it changes, since vectors from two model versions aren't comparable inside the same index. | `MLflow Model Registry (self-hosted)`, `DVC` |
| **Vector-index freshness/staleness** | a defined SLA bounds how long a changed or deleted source document can sit un-reflected in the index, verified by an incremental sync job rather than trusted from a one-time full load. | `LlamaIndex IngestionPipeline (docstore upsert/delete)`, `Airflow`, `Dagster` |
| **Vector-DB backup/restore verification** | the index itself — not just the source documents it was built from — can be rebuilt or restored from a snapshot on a tested schedule; several popular self-hosted vector DBs still ship no first-party restore path at all. | `Qdrant snapshots`, `Weaviate backup module`, `milvus-backup`, `chromadb-ops (community, partial)` |
| **Retrieval quality evaluation** | precision/recall@k, MRR, or NDCG measured against a labeled query-to-relevant-chunk eval set, not a smoke test that just confirms the pipeline returns something. | `LlamaIndex RetrieverEvaluator`, `Ragas`, `pytrec_eval / BEIR` |
| **Permission-aware retrieval (ACL leakage)** | retrieval respects the source document's original access controls — a chunk from a file User A can't open must never surface in User A's answer — tested explicitly, since flattening documents into a vector index is exactly what tends to flatten away their ACLs too. | `Qdrant/Weaviate metadata filtering`, `OpenFGA`, `custom ACL-leakage test suite` |
| **Source attribution/citation correctness** | a generated answer's individual claims can be traced back to the specific source chunk(s) that supposedly support them, with that link tested at the claim level instead of assumed because a citation number got printed. | `RAGChecker`, `Ragas (context recall)` |
| **Hallucination-rate evaluation harness** | a repeatable, scored check of whether generated answers are actually grounded in the retrieved chunks versus fabricated or pulled from the model's own parametric memory. | `Ragas (faithfulness)`, `TruLens (RAG triad)`, `DeepEval` |
| **Retrieval-quality drift monitoring (production)** | retrieval precision/recall is re-checked continuously against live traffic, not just once at ship time, since real queries and the corpus both drift and can quietly degrade a pipeline long after the original eval set stopped being representative. | `Evidently AI`, `Arize Phoenix` |
| **Cost-per-query tracking** | embedding and inference spend is measured per query/request rather than as one monthly total, since a growing corpus and chattier retrieval (more chunks, reranking, multi-hop) can silently balloon per-query cost. | `Langfuse`, `Helicone` |
| **Practice-maturity benchmarking** | the team has explicitly benchmarked its retrieval/eval practice against information-retrieval and search-engineering methodology — precision, recall, and NDCG carry decades of rigor — rather than reinventing ad hoc metrics, with a written note closing any gap still found below that bar. | `pytrec_eval (trec_eval)`, `BEIR`, `MADR template (gap-closing note)` |
