# AI Knowledge-Base / Agent-Context Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| almost entirely `.md`/`.mdx` files with structured YAML frontmatter (tags/priority/last_verified), no application source, meant to be read by an agent rather than compiled or run | `find . -iname "*.md" | wc -l` against total tracked files · inspect frontmatter schema |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Content freshness/staleness for AI consumption** | a last-verified date per file checked against a hard TTL in CI that fails the build — not just flags it — once exceeded, since an agent has no way to discount stale context the way a human skimming a doc would. | `front-matter last_verified + CI hard-fail gate (custom)`, `git log staleness script` |
| **Context-window budget discipline** | a token-count ceiling enforced per file and for the whole corpus in CI, so one bloated file or slow corpus creep can't silently crowd out higher-value context from the agent's window. | `Repomix (--token-budget CI gate)`, `tiktoken (custom per-file counting script)` |
| **Structured-metadata/frontmatter schema validation** | tags/type/priority and every other machine-parsed frontmatter field validated against a JSON Schema in CI, so a malformed field fails the build instead of silently breaking retrieval with no visible symptom. | `remark-lint-frontmatter-schema`, `remark-lint-frontmatter-validation`, `Ajv` |
| **Retrieval accuracy testing** | a fixed set of realistic queries run against the live retrieval pipeline with a judged list of expected files/passages, scored as a real eval (precision/recall/NDCG) instead of assumed from a manual spot-check. | `Ragas`, `DeepEval`, `Quepid` |
| **Redundancy/conflict detection across files** | pairwise semantic-similarity clustering plus an LLM-judge pass over the clustered set flags files giving an agent contradictory instructions, since an agent silently picks one side of a conflict instead of noticing it the way a human reader would. | `sentence-transformers (embedding-similarity script, custom)`, `LLM-judge contradiction pass (custom, per knowledgebase_guardian pattern)` |
| **Access-scope correctness** | which agent/team a document collection is scoped to enforced at the retrieval layer itself — tenant or row filters on the vector store — not just by folder convention or trust that nothing queries the wrong index. | `pgvector + Postgres row-level security`, `Weaviate (self-hosted, native multi-tenancy)`, `OPA (policy-as-code scope rules)` |
| **Practice-maturity benchmarking** | a written comparison of this repo's retrieval-evaluation and access-control practices against the decades-old disciplines they map to — information-retrieval relevance testing, enterprise content-access control — with a dated gap-closing note for every practice that falls short of that bar. | `TREC-style judged relevance methodology (via Quepid / OpenSearch Search Relevance Workbench)`, `written gap-closing note (custom doc)` |
