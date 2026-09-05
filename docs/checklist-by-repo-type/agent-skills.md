# Agent-Skills / Tool-Definition Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `SKILL.md` files, a `.claude/skills/` or `.mcp/` directory, or JSON/YAML tool-schema definitions consumed by an agent runtime | `find . -iname SKILL.md -o -iname mcp.json` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Schema validation of tool/function definitions** | the declared JSON-Schema input/output for every tool validated in CI, then cross-checked that the live implementation actually accepts/returns what's declared instead of drifting silently after a handler change. | `Ajv`, `Pydantic (Python / FastMCP)`, `Zod (TypeScript / MCP SDK)`, `MCP Inspector (exercises the live schema against the running server)` |
| **Least-privilege capability scoping** | each tool/skill's declared permissions and data access audited against what the task actually needs, the same way an overprivileged IAM role or OAuth scope gets flagged in a conventional access review. | `mcp-scan`, `agent-audit`, `OPA` |
| **Prompt-injection resistance testing** | the tool's handling of adversarial content embedded in the untrusted data it processes — a scraped page, a PDF, pasted user text — red-teamed with automated injection probes instead of trusted to hold by inspection. | `Garak`, `PyRIT`, `Promptfoo (redteam plugin)`, `Rebuff` |
| **Description/triggering-accuracy evaluation** | a repeatable eval that feeds realistic prompts through the full tool roster and checks whether the model actually calls the intended tool — and skips the wrong one — not just that the tool works once invoked by hand. | `Promptfoo (tool-call-f1 assertion)`, `DeepEval (ToolCorrectnessMetric)`, `Gorilla / Berkeley Function-Calling Leaderboard (AST-matcher method, adapt locally)` |
| **Tool-call determinism/replay testing** | a recorded tool call — arguments in, result out — replayed as a fixture in CI so a regression test runs deterministically offline, with no live model and no real external side effect in the loop. | `vcr-langchain`, `langchain-replay`, `pytest-recording / VCR.py (adapted)` |
| **Versioning/backward compatibility for tool signatures** | a diff between the old and new declared schema classified as additive vs. breaking before merge, the same discipline already applied to any other versioned API surface. | `json-schema-diff`, `json-schema-diff-validator`, `oasdiff (OpenAPI-derived tool schemas)`, `buf breaking (protobuf-based tool defs)` |
| **Practice-maturity benchmarking** | a written comparison of this repo's schema-versioning and permission-scoping practices against the decades-old disciplines they map to — REST/OpenAPI design, SemVer, OAuth-scope least privilege — with a dated gap-closing note for every practice that falls short of that bar. | `OWASP API Security Top 10 checklist`, `Spectral (custom ruleset against house tool-schema conventions)`, `SemVer spec conformance review` |
