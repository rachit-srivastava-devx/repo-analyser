# Checklist by Repo Type

One audit checklist per repo archetype, split out of the full [Repo Audit Field Guide](../repo-audit-field-guide.html) so each type is a single, skimmable file. Every table follows the same three columns: Criterion, What It Checks, Tools (keyless-first) — a tool marked *(keyed)* needs a paid/managed account; everything else is free, OSS, or self-hostable.

Start here if you don't already know what you're looking at: [Detecting Repo Type](detecting-repo-type.md).

## Repo Architecture

How the codebase is split across git history, not what it's for.

| Repo Type | Checklist | Criteria |
|---|---|---|
| Single Repo | [single-repo.md](single-repo.md) | 124 |
| Monorepo | [monorepo.md](monorepo.md) | 43 |
| Polyrepo | [polyrepo.md](polyrepo.md) | 86 |
| Microservices | [microservices.md](microservices.md) | 89 |

## Meta & Content-Purpose Repos

Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.

| Repo Type | Checklist | Criteria |
|---|---|---|
| Meta-Repo / Manifest Repo | [meta-repo.md](meta-repo.md) | 10 |
| Library/Package Repo | [library-package.md](library-package.md) | 17 |
| Infra/GitOps Repo | [infra-gitops.md](infra-gitops.md) | 13 |
| Docs Repo | [docs-repo.md](docs-repo.md) | 11 |
| Developer Tools Repo (CLI/SDK/Plugin) | [developer-tools.md](developer-tools.md) | 6 |
| QA / Testing Infrastructure Repo | [qa-testing-infrastructure.md](qa-testing-infrastructure.md) | 4 |
| ML / Data Science Repo | [ml-data-science.md](ml-data-science.md) | 10 |
| RAG / Vector-Store Repo | [rag-vector-store.md](rag-vector-store.md) | 12 |
| AI Knowledge-Base / Agent-Context Repo | [ai-knowledge-base.md](ai-knowledge-base.md) | 7 |
| Agent-Skills / Tool-Definition Repo | [agent-skills.md](agent-skills.md) | 7 |
| Smart Contract / Blockchain Repo | [smart-contract.md](smart-contract.md) | 6 |
| Mobile App Repo (iOS/Android) | [mobile-app.md](mobile-app.md) | 6 |
| Design System / Component Library Repo | [design-system.md](design-system.md) | 5 |
| Embedded / Firmware Repo | [embedded-firmware.md](embedded-firmware.md) | 6 |
| Data-Pipeline / ETL Repo | [data-pipeline-etl.md](data-pipeline-etl.md) | 6 |
| Browser Extension Repo | [browser-extension.md](browser-extension.md) | 5 |
| Other Emerging Archetypes (Game Engines & Multi-Agent Orchestration) | [emerging-archetypes.md](emerging-archetypes.md) | 4 |

## Cross-Cutting Analysis

Not a repo shape — a different scope of audit layered on top of whichever type(s) above actually apply.

| Scope | Checklist | Criteria |
|---|---|---|
| Portfolio & Process | [portfolio-process.md](portfolio-process.md) | 3 |
| Per-Pull-Request Review | [pr-review.md](pr-review.md) | 28 |

**Total: 21 repo-type checklists + 2 cross-cutting checklists, 508 criteria, plus the detection guide above.**

Generated from [`repo-audit-field-guide.html`](../repo-audit-field-guide.html) — that HTML file is the single source of truth; regenerate these files from it rather than hand-editing when the guide changes.
