# Architecture Decision Records

One file per real architectural decision — not every change, only the ones a future contributor
would otherwise have to reverse-engineer from a diff. Numbered sequentially, never renumbered or
deleted; a reversed decision gets a new ADR that supersedes the old one and says so.

Template for a new entry:

```markdown
# ADR-NNNN: <decision, as a sentence>

- **Status:** Accepted | Superseded by ADR-NNNN

## Context
What was actually observed (a real bug, a real scaling problem) that made the old approach wrong
or insufficient. Not a hypothetical.

## Decision
What changed, concretely.

## Consequences
What got harder, what got easier, what must be true going forward for this decision to keep
holding (the thing a reviewer should check for in a future PR that touches this area).
```

## Log

| ADR | Decision |
|---|---|
| [0001](0001-fail-loud-not-silent.md) | A module returns real data or raises — never a silent empty result |
| [0002](0002-src-layout-package-split.md) | `src/repo_analyser/{core,collectors,graph,synthesis,reporting}/` over a flat package |
