# posx — Test *Quality*

*Not "has a test script" (a proxy) -- every repo's unit-test script was **actually executed**
and its real pass/fail summary parsed from the runner's own output. Scoped to unit tests only
(integration suites needing live infrastructure are out of scope for an unattended run --
see `docs/METHODOLOGY.md`). CI-gate status is from parsing actual workflow step contents, not
inferred from a workflow file's existence. Data: `testquality_runs.csv`, `ci_gates.csv`.*

## 1. CI enforcement

**1 of 26 repos** have a CI workflow that runs tests on any trigger. The
rest configure CI for build/deploy only.

## 2. Real, executed test results

| Repo | Script | Runner | Passed | Failed | Total | Node used | Note |
|---|---|---|---|---|---|---|---|
| posx-comet-admin | test | vitest | 1 | 0 | 1 | v20.20.2 |  |
| posx-comet-backend | test:unit | jest | 3 | 3 | 6 | v20.20.2 |  |
| posx-demo-admin | test | vitest | 0 | 1 | 1 | v20.20.2 |  |
| posx-demo-backend | test:unit | jest | 0 | 0 | 0 | v20.20.2 | jest ran, testMatch pattern matched zero files --  |
| posx-eume-admin | test | vitest | 0 | 1 | 1 | v20.20.2 |  |
| posx-eume-backend | test:unit | jest | 169 | 10 | 179 | v20.20.2 |  |
| posx-frido-admin | test | vitest | 17 | 1 | 18 | v20.20.2 |  |
| posx-frido-b2b-admin | test | vitest | 1 | 0 | 1 | v20.20.2 |  |
| posx-frido-b2b-backend | test:unit | jest | 0 | 0 | 0 | v20.20.2 | jest config validation error -- suite never starte |
| posx-frido-backend | test:unit | jest | 36 | 0 | 36 | v20.20.2 |  |
| posx-frido-mobility-admin | test | vitest | 0 | 1 | 1 | v20.20.2 |  |
| posx-frido-mobility-backend | test:unit | jest | 0 | 0 | 0 | v20.20.2 | jest ran, testMatch pattern matched zero files --  |
| posx-mokobara-admin | test | vitest | 0 | 1 | 1 | v20.20.2 |  |
| posx-mokobara-backend | test:unit | jest | 162 | 0 | 162 | v20.20.2 |  |
| posx-mokobara-clearance-backend | test:unit | jest | 0 | 0 | 0 | v20.20.2 | jest ran, testMatch pattern matched zero files --  |
| posx-ugaoo-admin | test | vitest | 64 | 6 | 70 | v20.20.2 |  |
| posx-ugaoo-backend | test:unit | jest | 852 | 7 | 859 | v20.20.2 |  |

**4** repos fully passing right now.
**9** have real failures right now.
**3** have a working test harness
that matches zero actual test files. **1** have
a broken test configuration that prevents the suite from starting at all.
**9** have no unit-test script.

## 3. Honest limitations

- Integration/e2e test scripts are not executed by this module (they typically need live
  infrastructure this analysis has no access to) -- a repo could have a much larger, currently
  broken integration suite invisible here.
- A repo's runtime environment (Node/Python/Go version) can cause a false failure unrelated to
  the code under test -- this tool pins to the target's own declared engine version where it
  can detect one and records which runtime actually ran each suite (`node_version_used` /
  equivalent), but a mismatch it can't auto-correct will still show as a false failure. Check
  the raw log before treating any single failure as confirmed.

*Raw data: `testquality_runs.csv`, `ci_gates.csv`. Raw logs regenerate via the `testquality`
module (not archived).*
