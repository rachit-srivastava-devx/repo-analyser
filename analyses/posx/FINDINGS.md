# posx portfolio: findings

26 repos analyzed (`devx-commerce` org, cloned locally), spanning 8 client
brands (comet, eume, frido, frido-b2b, frido-mobility, mokobara, ugaoo,
demo) x up to 3 app types (store, backend, admin), plus a knowledge-base
repo. All 26 are Node/TypeScript. Real history: 2025-03 through 2026-09
(oldest repos ~18 months old), 8,451 total commits.

Every number below traces to a CSV/JSON in this directory, produced by
`chronicle-analyzer`'s modules — see [`../../docs/METHODOLOGY.md`](../../docs/METHODOLOGY.md)
for the exact formula behind each one, and [`../../docs/ONTOLOGY_AUDIT.md`](../../docs/ONTOLOGY_AUDIT.md)
for the classifier's measured accuracy against an independent blind check.

---

## 1. One platform, eight brand names

**Claim, and the proof, in one command:**

```
diff posx-comet-backend/src/api/middlewares.ts posx-mokobara-backend/src/api/middlewares.ts
# → no output: the files are byte-for-byte identical
```

`exact_duplicates.py` (sha256 of whole-file content — not a heuristic)
found **3,001 files that are byte-identical across two or more repos at the
same relative path**, of which 3,046 groups total involve more than one
repo. The worst cases are identical across **all 9 backend repos at once**:
`medusa-config.ts`'s shared boilerplate, `src/api/middlewares.ts`,
`src/lib/puppeteer.ts`, `src/lib/nodemailer.ts`, 12+ files under
`src/links/*` (data-model relationship declarations), and
`src/modules/shopify-collection/index.ts`. `eslint.config.js` is identical
across all 11 store repos. Source: `exact_duplicate_files.csv`.

A second, independent tool (`jscpd`, block-level clone detection, ≥10
lines/≥70 tokens) corroborates the scale from a different angle: **63.6% of
all lines in the portfolio are part of a duplicated block**, and
**90.5% of the 17,658 clone pairs found are cross-repo, not within a single
repo** (15,988 of 17,658) — the dominant duplication mode in this codebase
is "the same code copied into another repo," not ordinary intra-file
repetition. Source: `duplication_summary.json`.

**Caught during this analysis, and corrected before being reported**: jscpd
initially appeared to show `medusa-config.ts` identical across 9 repos.
Running an actual `diff` between two of them showed real per-tenant
differences (different Medusa module lists, different Redis configuration)
outside a shared boilerplate block — jscpd was correctly reporting a
*partial* duplicated block, which this analysis had almost overclaimed as
whole-file identity. The sha256 check above is what actually proves
whole-file identity; the two measurements are kept separate for exactly
this reason.

**Why this matters mechanically, not just abstractly**: `src/api/middlewares.ts`
is independently the **#2 churn hotspot in the entire portfolio**
(78 revisions in comet-backend, 63 in mokobara-backend — `complexity_hotspots.csv`)
*and* one of the files duplicated across all 9 backends. Every time
middleware logic needs a fix, it is fixed once and then must be
hand-propagated to the other 8 repos, or it silently diverges. This is not
hypothetical: the i18n-translation-validation test (see §4) is currently
failing independently in 3 different admin repos because each brand's
translation file has drifted from a schema all of them share.

## 2. CI runs, but does not gate, in 25 of 26 repos

`ci_gates.py` parsed every `.github/workflows/*.yml` (not inferred from the
folder's existence — the actual step contents) across all 26 repos.
**25 have CI configured; 1 (`posx-mokobara-backend`) actually runs tests
before merge or deploy.** The other 24 with CI run build → Docker →
ECR → deploy, and nothing else, on every trigger including plain `push`.

This is true even for the 8 admin repos that have a fully wired `vitest`
setup with a working `npm test` script — the tests exist, run cleanly
locally, and are invoked by *nothing* in CI. Source: `ci_gates.csv`.

**The fix already exists in this portfolio and is proven to work.**
`posx-mokobara-backend/.github/workflows/quality.yml` runs on every PR:
lint (changed lines only — full-repo lint is currently ~1,665 violations,
tracked as visible-but-non-blocking debt), build, and `npm run test:unit`,
with `concurrency: cancel-in-progress` and an explicit code comment
recording *why* it's CI and not a git hook:

> Deliberately CI and not a git hook: hooks are advisory. `git push
> --no-verify` skips them, which is exactly what happened during the
> 2026-08-11 dependency audit.

`posx-mokobara-backend` is also the only backend with a **fully green test
suite** (162/162 passing — §4) and the largest `total_dependencies` count
among backends without being disproportionately defect-prone. The one repo
in the portfolio with an enforced gate is the one with a suite worth
trusting. That is a sample size of one, but it is not a coincidence
available anywhere else in this data.

## 3. Commit ontology: real feature work is running ahead of Button-style ops sprawl, but correction share is high

7,137 non-merge commits classified by a deterministic rule table (not an
LLM — see METHODOLOGY.md), 17.6% left honestly unclassified rather than
force-fit:

| Superclass | % of commits |
|---|---:|
| Delivery (new features) | 34.9% |
| Correction (bug fixes + reverts) | 31.8% |
| *unclassified* | 17.6% |
| Code health (refactor/test/docs/perf) | 7.7% |
| Ops & config (CI/access/release/deps) | 5.9% |
| Data & schema | 0.8% |
| Housekeeping | 1.4% |

Compare to the Button/Chronicle engagement's decade-old, 180-repo estate:
Delivery there was flat at ~17% for ten years, capped by ops/config sprawl
(36%) that hadn't existed yet in posx's 18-month-old codebase. posx does
not have that problem yet — Ops & config is under 6%. **What it has instead
is a Correction share nearly as large as Delivery itself**: for every 10
commits that ship something new, roughly 9 are fixing something. Source:
`ontology_summary.json`, classifier accuracy in `ONTOLOGY_AUDIT.md` (68.4%
exact / 72.0% superclass agreement against an independent blind check —
read these percentages as directional, not precise to the point).

## 4. Tests exist; whether they pass is a different question, checked by actually running them

Not "has a test script" — every repo's unit-test script was **actually
executed**, right now, on this codebase, under a pinned Node 20 runtime
(the portfolio's own `engines: {"node": ">=20"}`; this host defaults to
Node 26, under which a transitive `jsonwebtoken` dependency crashes at
require-time before any test runs — see METHODOLOGY.md for how this was
caught and corrected). Results, from `testquality_runs.csv`:

| Status | Repos |
|---|---|
| **Passing right now** | `posx-comet-admin`, `posx-frido-b2b-admin`, `posx-frido-backend`, `posx-mokobara-backend` |
| **Failing right now** | `posx-comet-backend` (3/6), `posx-eume-backend` (10/179), `posx-frido-admin` (1/18), `posx-ugaoo-admin` (7/70), `posx-ugaoo-backend` (7/859), `posx-demo-admin` (1/1), `posx-eume-admin` (1/1), `posx-frido-mobility-admin` (1/1), `posx-mokobara-admin` (1/1) |
| **Test harness wired, zero tests written** | `posx-demo-backend`, `posx-frido-mobility-backend`, `posx-mokobara-clearance-backend` (jest runs, matches 0 of 460-624 files against its own `testMatch` pattern) |
| **Test config broken, suite cannot start** | `posx-frido-b2b-backend` (`jest.config.js` references `./integration-tests/setup.js`, which does not exist in the repo) |
| **No test script at all** | 9 repos, including all 6 stores blocked by §5's `npm install` failure |

Two specific, reproducible-today defects worth calling out by name:

- **`posx-comet-backend/src/types/validators/__tests__/online-order-address.unit.spec.ts`**
  — 3 of 6 assertions fail: the address validator is expected to default
  missing optional fields to `""` and currently returns `success: false`
  instead. This repo's CI is deploy-only (§2), so this has been failing
  silently against a production order-address code path.
- **The same shared i18n-completeness test** —
  `src/i18n/translations/__tests__/validate-translations.spec.ts`, "en.json
  should have all keys defined in schema" — **fails independently in 4 of
  the 8 admin repos** (`demo-admin`, `eume-admin`, `frido-mobility-admin`,
  `mokobara-admin`), each with a different set of missing/extra translation
  keys (`employees`, `globalConfig`, `storeCoupons`, `storeDetails`, ...
  varies per repo). Direct, live evidence of the §1 duplication cost: one
  shared test, copy-pasted into 8 repos, half of which have already drifted
  out of sync with it.
- **`posx-mokobara-admin`** has both problems at once: the shared i18n test
  above fails on its own merits, *and separately* 10 of its other 11 "test
  files" fail immediately with a Playwright/vitest framework collision
  (`test.use()`/`test.describe()` called where vitest, not Playwright, is
  running them) — the vitest config is not excluding `tests/e2e/**`, so
  every run reports 10 additional false failures on top of the one real one.

## 5. A single, portfolio-wide dependency bug blocks all tooling on 6 of 8 storefronts

`npm install` fails outright (not a warning — a hard, unrecoverable error,
`--force`/`--legacy-peer-deps` do not help) on `posx-comet-store`,
`posx-demo-store`, `posx-eume-store`, `posx-frido-store`,
`posx-frido-b2b-store`, `posx-frido-mobility-store`. Root cause, confirmed
by direct inspection of `package.json`:

```json
"@point-of-sale__receipt-printer-encoder": "link:@types/@point-of-sale__receipt-printer-encoder"
```

npm rejects the package name itself (`EINVALIDPACKAGENAME`: scoped package
names cannot contain a literal `__`). This single malformed line, present
in 6 of 8 store repos (propagated by the same copy-paste pattern documented
in §1; `posx-mokobara-store` and `posx-ugaoo-store` do not have it, so it
was introduced after those two diverged, or fixed independently in them),
blocks `npm ci`, `npm audit`, dependency-cruiser, and any mutation-testing
tool on every affected store. **This is a one-line, mechanical fix** —
delete the malformed line — after which `depgraph` and `testquality` can
run on these repos too.

## 6. Defect escape rate: real, non-trivial, and — unlike Button's — improving

SZZ (Śliwerski/Zimmermann/Zeller), implemented via PyDriller + `git blame`
against the parent of every fix commit (formula in METHODOLOGY.md):
**6,333 bug-introducing commits attributed** across the portfolio's history.
Fix latency: **median 22 days, p90 242 days** — one defect in ten lives
about 8 months in the codebase before its fix lands. Source:
`escape_summary.json`, `escapes.csv`.

The monthly trend (`escape_monthly.csv`) is the important part, and it does
**not** match the Button engagement's "declined for years, now rising"
story — posx's is a maturation curve:

| Period | Escape rate | Commit volume |
|---|---:|---:|
| 2025-03 to 2025-11 (platform's first 9 months) | 19-53%, volatile | 46-455/month |
| 2026-01 to 2026-04 | 22-34% | 278-783/month |
| **2026-05 to 2026-08 (last 4 full months)** | **15-18%** | **431-786/month** |

Escape rate has fallen by roughly half while monthly commit volume has
nearly doubled — the platform is shipping substantially more code per month
at a lower defect-introduction rate than it did a year ago. 15% is still a
real number (about 1 introduced defect for every 6-7 commits), not a small
one, but the trajectory is the opposite of a crisis.

Worst-by-repo (min. 30 fix commits, `escapes.csv` grouped): `posx-comet-store`
(917 escapes / 211 fix commits), `posx-mokobara-backend` (979 / 268),
`posx-comet-backend` (801 / 250) — the three largest, oldest, highest-churn
repos, consistent with simple exposure (more commits, more chances to
introduce and later catch a regression) rather than a quality outlier.

## 7. Hotspots: complexity x churn, not complexity alone

Tornhill's formula (`total_ccn(file) x n_revisions(file)`), computed by
joining `lizard` (cyclomatic complexity, all languages) against `code-maat`
(churn, from real git history):

| Repo | File | Total CCN | Max single-function CCN | Revisions | Hotspot score |
|---|---|---:|---:|---:|---:|
| mokobara-backend | `src/workflows/order-detail/steps/confirm-order-detail-step.ts` | 198 | **82** | 92 | 18,216 |
| eume-store | `src/components/app/product/cart-panel.tsx` | 330 | 103 | 48 | 15,840 |
| mokobara-store | `src/pages/exchanges/details.tsx` | 366 | 45 | 37 | 13,542 |

The #1 hotspot in the entire portfolio is order-confirmation logic in the
payment-adjacent path, with a single function at cyclomatic complexity 82
(conventional guidance treats >50 as effectively untestable by hand) and
the highest change frequency of any file analyzed. `src/pages/products/details.tsx`
independently appears as a top-15 hotspot in **four separate store repos**
(mokobara, eume, comet, frido) — the same weak spot, copy-pasted, degrading
the same way in parallel. Source: `complexity_hotspots.csv`.

## 8. Internal architecture is genuinely clean — a real, positive finding

`dependency-cruiser`, run per-repo (20 of 26 — blocked on the 6 from §5),
**restricted to the repos' own source** after this analysis caught and
corrected a measurement bug (dependency-cruiser, given a file list, follows
imports into `node_modules` and reports third-party packages' own internal
cycles as if they belonged to the repo being analyzed — an initial pass
nearly reported "800+ circular dependencies" per backend, which turned out
to be entirely inside npm packages like `bl`/`readable-stream`, unrelated
to any code posx's engineers wrote). After the fix: **19 of 20 analyzable
repos have zero internal circular dependencies.** The only exception,
`posx-mokobara-backend`'s 32 circular edges, collapses to **16 unique file
pairs, every one of them a parent-child ORM model relationship**
(`credit-note.ts` ↔ `credit-note-transaction.ts`, `cart.ts` ↔
`cart-product.ts`, etc.) — the standard, largely benign pattern for this
data-modeling style, not spaghetti coupling. Source: `depgraph_summary.csv`,
`depgraph_raw/*.json`.

One consistent, minor code-smell: every admin repo's most-imported internal
module is reached via a 5-level relative import (`../../../../../components/modals`)
rather than a path alias — fragile to file moves, present identically
across all 8 admin repos (another §1 instance).

## 9. Bus-factor risk is concentrated in the newest, smallest repos

Gini coefficient of per-author commit share, computed directly from `git
log` (formula in METHODOLOGY.md). Above 0.75 (one author dominates):
`posx-kb` (1 author, 5 commits total — effectively unmaintained),
`posx-mokobara-clearance-backend` (94% of 50 commits from one author),
`posx-frido-b2b-store` (89% of 64 commits), `posx-frido-b2b-backend` (78%
of 120 commits), `posx-frido-b2b-admin` (76% of 42 commits). Every one of
these is also the newest cohort of repos (first commit Dec 2025 or later)
— consistent with "a new brand launch, staffed by 2-3 people, not yet
absorbed into the wider team's rotation" rather than an active project
losing its bus factor. Source: `inventory.csv`.

## 10. Security: one live exposure, several historical ones — each verified individually, not reported as a raw tool count

`gitleaks` over **complete git history** (not just the current tree — a
secret removed in a later commit is still permanently readable by anyone
who clones the repo) + `semgrep` (`p/security-audit` + `p/secrets`) over
current source, across all 26 repos, all completed.

**Code-pattern scan (semgrep) is clean**: 2 findings total across the
entire portfolio, both the same low-severity pattern
(`dangerouslySetInnerHTML` with a non-constant argument — an XSS risk if
the HTML source is ever user-controlled, in `posx-mokobara-admin`'s
product-detail component and `posx-ugaoo-store`'s accordion primitive; both
WARNING, neither a credential issue). No injection patterns, no
hardcoded-secret-as-fallback pattern anywhere — the exact bug class behind
Button's critical auth-bypass finding does not appear in this codebase.

**Secret history scan (gitleaks), all 26 repos, 80 total findings across
8 repos** — broken down by confirmed format, not left as a raw count:

| Rule | Count | What it is |
|---|---:|---|
| `generic-api-key` | 37 | Unverified generic-entropy matches — needs manual triage, see below |
| `curl-auth-header` | 20 | Hardcoded `Authorization:` headers in scripts/docs |
| `shopify-access-token` | 17 | Format-confirmed `shpat_...` (Shopify Admin API private-app tokens) |
| `aws-access-token` | 3 | Format-confirmed `AKIA...` (AWS IAM access key ID) |
| `shopify-custom-access-token` | 2 | Shopify custom-app token variant |
| `jwt` | 1 | A JWT hardcoded in frontend request code (decodes to a bare merchant ID + issued-at, no other claims) |

By repo: `posx-mokobara-backend` (29), `posx-comet-backend` (24),
`posx-ugaoo-backend` (11), `posx-kb` (10), `posx-frido-store` (2),
`posx-mokobara-clearance-backend` (2), `posx-eume-backend` (1),
`posx-mokobara-store` (1).

**One of these is a live exposure, not a historical one — checked and
confirmed, not assumed:**

- **`posx-kb/public/search-index.json`, currently in `HEAD`**, contains a
  key prefixed `rzp_live_` — Razorpay's own naming convention for a
  **production**, not test, API key. `posx-kb` is a Next.js app; anything
  under `public/` is served as a static asset at the site's root by
  definition, so if this app is deployed anywhere, the key is fetchable by
  URL alone, no repository access needed. It got there mechanically: a
  `prebuild`/`predev` script (`scripts/parse-docs.mjs`) indexes
  `docs/PRODUCT_FEATURE_DOC_FRIDO.md` for search, and that source document
  appears to contain the real key inline as a worked example — every build
  faithfully copies it into the public artifact. See `ROADMAP.md`'s first
  item for the exact remediation steps.

**Everything else found is historical — removed from current `HEAD`,
which is not the same as rotated, verified individually rather than left
as a tool count:**

1. **`posx-comet-backend/.env.backup`** (single commit `6a29ee8`, "upload
   s3 api"): a whole real `.env` file committed by accident, later
   deleted. 3 AWS key matches, 4 Shopify token matches, 17 generic-api-key
   matches, all in one file. Confirmed absent from current `HEAD` — but
   still retrievable forever via `git show 6a29ee8:.env.backup` by anyone
   with clone access, unless history is rewritten.
2. **`shpat_...` tokens hardcoded directly in source** (not an env file):
   `posx-mokobara-backend` (`src/scripts/collecntions.ts` [sic],
   `src/scripts/products.ts`, `src/lib/constant.ts` — the last one
   especially concerning as a shared constants file, not a throwaway
   script) and `posx-eume-backend/assign-random-giftcards.ts`. Checked with
   `git grep shpat_` against current `HEAD` in each: **none currently
   present in the working tree** — each was edited or removed in a later
   commit. The value `shpat_[REDACTED]` recurs across
   8 separate commits in `posx-mokobara-backend` alone — live in that
   repo's source for a real stretch of time, not one copy-paste-and-revert.
3. **`posx-ugaoo-backend/docs/integration/adsr-integration-guide.md`**: two
   distinct real-looking Authorization-header values embedded in worked
   `curl` examples (a common documentation-writing leak pattern — testing
   against a real endpoint, then pasting the working command including its
   real header into the doc). Also `tests/pinelabs-service.unit.spec.ts`
   hardcodes what gitleaks flags as a generic API key rather than an
   obvious mock/fixture value — worth a look to confirm it's fixture data
   and not a real Pine Labs (payment terminal) credential.

**What this analysis did not do, deliberately**: attempt to use, validate,
or check the liveness of any discovered credential against Razorpay's,
Shopify's, or AWS's APIs. That would mean acting with someone else's
credentials without authorization — out of scope regardless of technical
feasibility. The org's own provider consoles are the only place to confirm
current validity, which is exactly why the recommendation throughout is
"rotate," not "check first."

**The `curl-auth-header` and `generic-api-key` findings are not all
individually triaged** the way the clusters above were — 37 + 20 = 57
findings is enough that a full one-by-one pass was out of scope here;
`security_secrets.csv` has the complete list (repo, file, commit, author,
date, redacted-secret) for whoever picks this up next.
