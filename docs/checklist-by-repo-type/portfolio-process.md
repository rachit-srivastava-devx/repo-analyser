# Portfolio & Process

Metrics that only make sense looking across the whole engineering org over time, or auditing the audit itself — not a property of any single repo.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **Audit scope names an org/team, or spans 10+ repos over time, rather than one clone** | `a scope decision, not a file signal` |

## Audit Checklist

### Portfolio Analytics

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Commit-ontology mix over time** | classify every commit into delivery/correction/code-health/ops&config/data&schema/housekeeping, trend the mix monthly to see what share of engineering effort is actually new capability vs. plumbing and toil. | `git log --numstat classifier script`, `PyDriller`, `pandas` |
| **Contribution-inequality (Gini/Lorenz)** | measure how unevenly work is distributed across the whole team (top-10%/bottom-50% commit share), distinct from bus-factor's single-person risk on one module. | `custom Gini-coefficient script`, `git-quick-stats`, `numpy/scipy` |

### Audit Methodology Integrity

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Audit-the-audit** | validate your own audit methodology before findings ship: blind independent re-rating, criterion-validity correlation against real outcomes, cross-check against an independent system of record. | `blind re-rating protocol (script)`, `scikit-learn cohen_kappa_score`, `gh api cross-check` |
