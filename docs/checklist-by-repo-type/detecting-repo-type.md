# Detecting Repo Type

Check for these signals in roughly this order — most repos match on the first row that fits.
Per-Pull-Request criteria always layer on top of whichever else applies; it's never exclusive
of the rest.

## Original Signal Set

| Signal | Indicates | How to Check |
|---|---|---|
| **No workspace file; one manifest at root** (package.json, pyproject.toml, go.mod, Cargo.toml) | Single Repo | `default assumption when nothing below matches` |
| **nx.json, turbo.json, pnpm-workspace.yaml, lerna.json, or rush.json at root** | Monorepo (JS/TS ecosystem) | `marker-file check script` |
| **WORKSPACE, WORKSPACE.bazel, MODULE.bazel, BUCK, or pants.toml at root** | Monorepo (Bazel/Buck2/Pants) | `marker-file check script` |
| **Multiple independent manifests in sibling folders, no shared workspace file** | Monorepo, unmanaged | `verify no separate CI/build per folder before assuming polyrepo` |
| **.gitmodules with many entries and few other source files; or manifest.xml/.repo/ (AOSP repo tool); or west.yml (Zephyr)** | Meta-repo / manifest repo | `ls .gitmodules`, `cat manifest.xml` |
| **catalog-info.yaml (Backstage), or a Cortex/OpsLevel/Port config referencing sibling repos** | Polyrepo fleet with a registry | `file presence check` |
| **README/CODEOWNERS names sibling repo URLs; org has 10+ similarly-shaped repos** | One member of a polyrepo fleet | `gh repo list <org> (needs org-level context — not detectable from one clone)` |
| **Multiple Dockerfiles, or docker-compose.yml/k8s manifests declaring 2+ Deployments** | Microservices architecture | find . -iname Dockerfile \| wc -l, `docker-compose config --services` |
| **Istio/Linkerd CRDs (VirtualService, DestinationRule) or sidecar-injection annotations in YAML** | Microservices on a service mesh | `kubectl get virtualservices,destinationrules -A` |
| **package.json with main/exports/types, tagged semver releases, no Dockerfile/deploy manifests, listed on npm/PyPI/crates.io** | Library/package repo | `npm view <name> versions`, `registry API check` |
| **pyproject.toml with [build-system], or setup.py, plus PyPI classifiers** | Python library | `pip index versions <name>` |
| **Majority .tf/.tf.json, or Chart.yaml (Helm), or kustomization.yaml; CI runs plan/apply/helm template** | Infra/GitOps repo | `cloc --by-file-by-lang .`, `file-extension ratio` |
| **Majority .md/.mdx/.rst; docusaurus.config.js, mkdocs.yml, conf.py (Sphinx), or .vitepress present; no app source** | Docs repo | `cloc`, find . -iname "*.md" \| wc -l |
| **Audit scope names an org/team, or spans 10+ repos over time, rather than one clone** | Portfolio & Process | `a scope decision, not a file signal` |
| **A diff is attached to an open pull/merge request** | Per-Pull-Request Review | `CI event check (e.g. github.event_name == 'pull_request')` — always an overlay, never exclusive |

## Newer & Specialized Archetypes (2026-era)

These 13 repo types were added to the field guide after the signal table above was first
written; none of them had a detection heuristic yet. The marker files/configs below are the
same kind of "check for this first" signal as the table above, composed to close that gap
rather than extracted from an existing source.

| Signal | Indicates | How to Check |
|---|---|---|
| `bin` field in `package.json`, a `cmd/` directory (Go), `[project.scripts]` in `pyproject.toml`, or a VS Code extension's `package.json` with `contributes`/`engines.vscode` | Developer Tools Repo (CLI/SDK/Plugin) | `jq .bin package.json` · `grep -l project.scripts pyproject.toml` |
| repo publishes shared test fixtures, a Playwright/Cypress config preset, or CI-template workflows consumed by *other* repos — no product/app entry point of its own | QA / Testing Infrastructure Repo | check `package.json` `main`/`exports` point at test-helper code · grep other repos' `.github/workflows` for a `uses:` reference to this one |
| `.ipynb` notebooks, `dvc.yaml`/`.dvc` files, or a requirements file naming torch/tensorflow/scikit-learn/pandas as primary dependencies | ML / Data Science Repo | `find . -name "*.ipynb" | wc -l` · `cat dvc.yaml` |
| docker-compose or deployment config referencing Qdrant/Weaviate/Milvus/Chroma/pgvector, or a llama-index/langchain dependency paired with an ingest/chunking script | RAG / Vector-Store Repo | `grep -riE "qdrant|weaviate|milvus|chromadb|pgvector" docker-compose.yml requirements.txt package.json` |
| almost entirely `.md`/`.mdx` files with structured YAML frontmatter (tags/priority/last_verified), no application source, meant to be read by an agent rather than compiled or run | AI Knowledge-Base / Agent-Context Repo | `find . -iname "*.md" | wc -l` against total tracked files · inspect frontmatter schema |
| `SKILL.md` files, a `.claude/skills/` or `.mcp/` directory, or JSON/YAML tool-schema definitions consumed by an agent runtime | Agent-Skills / Tool-Definition Repo | `find . -iname SKILL.md -o -iname mcp.json` |
| `.sol` files, `foundry.toml`, `hardhat.config.js`/`.ts`, or `truffle-config.js` at root, with a `contracts/` directory | Smart Contract / Blockchain Repo | `find . -name "*.sol" | wc -l` · `test -f foundry.toml` |
| `.xcodeproj`/`.xcworkspace`/`Info.plist` (iOS), `AndroidManifest.xml` + `build.gradle` (Android), or `pubspec.yaml` (Flutter) / `app.json` + Expo config (React Native) | Mobile App Repo (iOS/Android) | `find . -iname Info.plist -o -iname AndroidManifest.xml` |
| `.storybook/` config plus a package that ships only UI components with no app entry point, often paired with a Style Dictionary/tokens config | Design System / Component Library Repo | `test -d .storybook` · `find . -iname "tokens*.json"` |
| `platformio.ini`, a Makefile targeting a cross-compiler (e.g. `arm-none-eabi-gcc`), `.ino` files, or vendor HAL/CMSIS directories | Embedded / Firmware Repo | `test -f platformio.ini` · `grep -l arm-none-eabi Makefile` |
| `dbt_project.yml`, a `dags/` directory (Airflow), or Dagster/Prefect project config, with no serving/app layer | Data-Pipeline / ETL Repo | `test -f dbt_project.yml` · `test -d dags` |
| `manifest.json` at root with a `manifest_version` key, no server-side code | Browser Extension Repo | `jq .manifest_version manifest.json` |
| `Assets/` + `ProjectSettings/` (Unity) or `.uproject` (Unreal); or a LangGraph/CrewAI/AutoGen dependency paired with a multi-agent orchestration entrypoint | Game Engine or Multi-Agent Orchestration Repo | `test -d Assets && test -d ProjectSettings` · `grep -lE "langgraph|crewai|pyautogen" requirements.txt` |
