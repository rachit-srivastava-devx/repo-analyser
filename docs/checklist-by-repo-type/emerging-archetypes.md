# Other Emerging Archetypes (Game Engines & Multi-Agent Orchestration)

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `Assets/` + `ProjectSettings/` (Unity) or `.uproject` (Unreal); or a LangGraph/CrewAI/AutoGen dependency paired with a multi-agent orchestration entrypoint | `test -d Assets && test -d ProjectSettings` · `grep -lE "langgraph|crewai|pyautogen" requirements.txt` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Frame-budget / performance regression (game/real-time engine)** | per-frame CPU/GPU cost is tracked against the platform's frame-time budget release-over-release, since a game has a hard real-time correctness bar a generic perf-regression check doesn't express. | `Unity Project Auditor`, `Unreal Insights / stat unit / stat gpu` |
| **Binary asset & memory budget validation (game/real-time engine)** | asset references and memory usage are validated against platform certification limits before submission, catching the class of bug that only a platform holder's own cert pass would otherwise find. | `Unreal Data Validation plugin`, `memreport -full` |
| **Cross-agent trace/replay (multi-agent orchestration)** | a multi-agent handoff — which agent called which tool, in what order, with what state — is captured and replayable, since a bug here is a distributed-systems bug wearing an AI costume. | `LangSmith`, `Langfuse`, `AgentOps` |
| **Agent-to-agent handoff governance (multi-agent orchestration)** | the control-flow/state-machine contract between agents is documented and reviewed as its own surface, distinct from any single agent's tool definitions — coordinate with the Agent-Skills/Tool-Definition dim above rather than duplicating it. | `written control-flow/state-machine review (custom)` |
