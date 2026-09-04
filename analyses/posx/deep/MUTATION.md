# posx — *Mutation* Testing

*Stryker: injects synthetic bugs (mutants) into a file and re-runs the test suite against each
one. A test suite that passes on unmutated code but also passes on a *mutated* one has not
actually verified that behavior -- mutation score (killed / covered mutants) answers "do these
tests catch a real defect," which passing-test-count alone cannot. Scoped deliberately: only
repos with a fully-passing unit suite were attempted (a failing suite has no meaningful
baseline), mutating only each repo's #1 complexity x churn hotspot (bounded runtime -- see
docs/METHODOLOGY.md for the install recipe this took three prior failed attempts to find).
Data: `mutation_results.csv`.*

## 1. Results

| Repo | File mutated | Mutants | Killed | Survived | No coverage | Score % |
|---|---|---|---|---|---|---|
| posx-mokobara-backend | src/workflows/order-detail/steps/confirm-order-detail-step.ts | 5 | 2 | 1 | 2 | 66.7 |

Scoped to the 4 repos with a fully-passing unit suite, mutating each repo's #1 complexity x churn hotspot only (bounded runtime -- Stryker needs a fresh local install per repo). 1 of 4 succeeded; the other 3 failed for repo-specific reasons (vitest-runner config, frido-backend jest setup) not chased further given time -- see mutation_results.csv skip_reason per row.

## 2. Honest limitations

- Attempted on 4 repos, succeeded on 1
  -- the others failed for repo-specific environment reasons (see `mutation_summary.json`'s
  `skip_reasons`), not chased further given time. This is a real, if narrow, data point per
  succeeding repo, not a portfolio-wide mutation posture.
- Only one file per repo was mutated (the highest hotspot) -- a low mutation score there is a
  real, specific finding about that file; it should not be generalized to "this repo's tests
  are bad" without checking other files.

*Raw data: `mutation_results.csv`.*
