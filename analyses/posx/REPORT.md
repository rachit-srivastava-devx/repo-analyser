# Chronicle Analyzer report: posx

Repos analyzed: 26
Modules completed: 1/1

## Repo activity

| repo | tier | total_commits | unique_authors | bus_factor_gini | top_author_share |
|---|---|---|---|---|---|
| posx-comet-backend | active | 1354 | 27 | 0.6633 | 0.2821 |
| posx-mokobara-backend | active | 1334 | 26 | 0.7902 | 0.3913 |
| posx-mokobara-store | active | 981 | 24 | 0.7212 | 0.3242 |
| posx-frido-backend | active | 936 | 21 | 0.6968 | 0.3141 |
| posx-comet-store | active | 930 | 26 | 0.6772 | 0.2774 |
| posx-eume-backend | active | 828 | 23 | 0.6468 | 0.2995 |
| posx-ugaoo-backend | active | 661 | 16 | 0.7108 | 0.3646 |
| posx-frido-store | active | 501 | 19 | 0.5826 | 0.2335 |
| posx-mokobara-admin | active | 419 | 23 | 0.6998 | 0.3866 |
| posx-eume-store | active | 411 | 21 | 0.4729 | 0.1995 |
| posx-ugaoo-store | active | 368 | 14 | 0.6848 | 0.3967 |
| posx-ugaoo-admin | active | 273 | 13 | 0.6374 | 0.4432 |
| posx-frido-admin | active | 267 | 16 | 0.6084 | 0.3483 |
| posx-comet-admin | active | 219 | 20 | 0.54 | 0.3607 |
| posx-eume-admin | active | 162 | 15 | 0.484 | 0.1975 |

_26 repos total; showing top 15 by commit count._

## CI gates

1/26 repos have a CI workflow that runs tests on any trigger.
| repo | has_ci_config | all_workflows_deploy_only |
|---|---|---|
| posx-comet-admin | True | True |
| posx-comet-backend | True | True |
| posx-comet-store | True | True |
| posx-demo-admin | True | True |
| posx-demo-backend | True | True |
| posx-demo-store | True | True |
| posx-eume-admin | True | True |
| posx-eume-backend | True | True |
| posx-eume-store | True | True |
| posx-frido-admin | True | True |
| posx-frido-b2b-admin | True | True |
| posx-frido-b2b-backend | True | True |
| posx-frido-b2b-store | True | True |
| posx-frido-backend | True | True |
| posx-frido-mobility-admin | True | True |
| posx-frido-mobility-backend | True | True |
| posx-frido-mobility-store | True | True |
| posx-frido-store | True | True |
| posx-kb | False | False |
| posx-mokobara-admin | True | True |
| posx-mokobara-clearance-backend | True | True |
| posx-mokobara-store | True | True |
| posx-ugaoo-admin | True | True |
| posx-ugaoo-backend | True | True |
| posx-ugaoo-store | True | True |


## Commit ontology

7137 non-merge commits classified (17.58% unclassified).

Superclass distribution (% of commits):

- correction: 31.81%
- other: 17.58%
- delivery: 34.87%
- code_health: 7.66%
- ops_config: 5.86%
- housekeeping: 1.44%
- data_schema: 0.77%

## Defect escape (SZZ)

6333 bug-introducing commits attributed.
Fix latency: median 22d, p90 242d.

## Top hotspots (complexity x churn)

| repo | file | total_ccn | n_revs | hotspot_score |
|---|---|---|---|---|
| posx-mokobara-backend | src/workflows/order-detail/steps/confirm-order-detail-step.ts | 198 | 92 | 18216 |
| posx-eume-store | src/components/app/product/cart-panel.tsx | 330 | 48 | 15840 |
| posx-mokobara-store | src/pages/exchanges/details.tsx | 366 | 37 | 13542 |
| posx-mokobara-store | src/pages/inventory/mark-inventory.tsx | 272 | 49 | 13328 |
| posx-eume-store | src/components/app/home/index.tsx | 291 | 41 | 11931 |
| posx-eume-store | src/pages/exchanges/details.tsx | 302 | 39 | 11778 |
| posx-mokobara-store | src/pages/products/details.tsx | 374 | 31 | 11594 |
| posx-eume-store | src/pages/products/details.tsx | 398 | 28 | 11144 |
| posx-comet-store | src/pages/products/details.tsx | 262 | 41 | 10742 |
| posx-frido-store | src/pages/online-orders/details/customer-details.tsx | 370 | 27 | 9990 |
| posx-mokobara-store | src/pages/orders/details/customer-details.tsx | 329 | 26 | 8554 |
| posx-frido-store | src/pages/products/details.tsx | 266 | 32 | 8512 |
| posx-ugaoo-store | src/components/app/product/cart-panel.tsx | 229 | 37 | 8473 |
| posx-mokobara-backend | src/modules/pdf-client/service.ts | 231 | 35 | 8085 |
| posx-ugaoo-backend | src/lib/helpers/build-summary.ts | 255 | 31 | 7905 |


## Duplication

jscpd (block-level, >=10 lines): 63.563972318073695% duplicated lines, 15988 cross-repo clone pairs.
Exact (sha256, whole-file): 3001 files are byte-identical across repos at the same path (max 9 repos for one file).

## Security

80 secrets found in git history (across 8 repos).
2 semgrep findings: {'WARNING': 2}

## Test quality (real execution)

17/26 repos have a runnable unit-test script.
0 repos have failing tests RIGHT NOW.

## Composite risk ranking

| repo | risk_score | escape_count | top5_hotspot_sum | exact_dup_file_count | ci_gate_missing | security_findings |
|---|---|---|---|---|---|---|
| posx-comet-backend | 0.5782 | 801 | 16233.0 | 245 | True | 24 |
| posx-mokobara-store | 0.5569 | 740 | 54442.0 | 107 | True | 1 |
| posx-mokobara-backend | 0.5307 | 979 | 40200.0 | 252 | False | 29 |
| posx-mokobara-admin | 0.5218 | 267 | 11542.0 | 1634 | True | 1 |
| posx-comet-store | 0.512 | 917 | 29891.0 | 123 | True | 0 |
| posx-eume-store | 0.4394 | 235 | 57587.0 | 224 | True | 0 |
| posx-frido-backend | 0.4362 | 666 | 17015.0 | 486 | True | 0 |
| posx-eume-admin | 0.4278 | 41 | 4375.0 | 1653 | True | 0 |
| posx-demo-admin | 0.42 | 1 | 835.0 | 1669 | True | 0 |
| posx-frido-mobility-admin | 0.4188 | 0 | 1133.0 | 1731 | True | 0 |

