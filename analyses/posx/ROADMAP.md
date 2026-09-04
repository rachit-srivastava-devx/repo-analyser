# posx portfolio: way forward

Ordered by (impact / effort), not by which finding is most dramatic. Each
item names the exact file(s) and the exact fix — nothing here requires
further investigation to start on.

## Do this first — before reading the rest of this document

### -1. `posx-kb` is currently serving a live Razorpay production key from a public URL, right now
Not a historical leak — this one is in the **current `HEAD`**, in
`public/search-index.json`, prefixed `rzp_live_` (Razorpay's own naming
for a production, not test, key). `posx-kb` is a Next.js app
(`next build`/`next start`); anything under `public/` is served as a
static asset at the site's root by definition — if this app is deployed
anywhere, that key is fetchable by anyone with the URL and a browser, no
repo access required. It reached the public file automatically: a
`prebuild`/`predev` script (`scripts/parse-docs.mjs`) ingests
`docs/PRODUCT_FEATURE_DOC_FRIDO.md` into a search index, and someone
appears to have put a real key inline in that doc as a worked example.

**Action, in order:**
1. Confirm in the Razorpay dashboard whether this key is still active.
   Assume yes until confirmed otherwise.
2. Rotate it regardless of (1) — a live production payment-gateway key is
   not one to leave live while checking.
3. Remove the key from `docs/PRODUCT_FEATURE_DOC_FRIDO.md`, then
   regenerate `data/knowledge.json`, `data/chunks.json`, and
   `public/search-index.json` (rerun `scripts/parse-docs.mjs` /
   `scripts/ingest.mjs`) so the regenerated artifacts no longer carry it.
4. Check whatever hosts this app (Vercel/similar) for cached/CDN copies of
   the old `public/search-index.json` that may outlive the redeploy.

### 0. Rotate the credentials found in git history (§10)
Not a code fix — a console action, and time-sensitive. Confirmed real
credential formats found in git history (removed from current `HEAD`, but
permanently retrievable by anyone with clone access via the commit SHA
below — deletion from the tip does not revoke them):

- **AWS access key `AKIA[REDACTED]`** — `posx-comet-backend`,
  `.env.backup`, commit `6a29ee8`. Rotate/deactivate in IAM; audit
  CloudTrail for any usage from an unrecognized source in the meantime.
- **Shopify Admin API token(s)**, format `shpat_...` — found across
  `posx-comet-backend` (`.env.backup`, commit `6a29ee8`),
  `posx-mokobara-backend` (`src/scripts/collecntions.ts`,
  `src/scripts/products.ts`, `src/lib/constant.ts`, recurring across 8
  commits), and `posx-eume-backend` (`assign-random-giftcards.ts`).
  Regenerate each affected store's private-app token in the Shopify admin.
- The full list, with file/commit/author/date for each (secrets
  themselves redacted), is in `security_secrets.csv` — the `curl-auth-header`
  and `generic-api-key` rows (46 total) still need a manual pass to
  separate real credentials from false positives; treat as unverified
  until reviewed, not as confirmed-safe.

This analysis did not and could not check whether these are still active —
that can only be confirmed in the AWS/Shopify consoles directly. Assume
compromised until rotated.

## Do this week (each is under a day of work)

### 1. Fix the storefront install blocker (§5)
Delete the malformed line from `package.json` in 6 repos:
```json
"@point-of-sale__receipt-printer-encoder": "link:@types/@point-of-sale__receipt-printer-encoder"
```
Repos: `posx-comet-store`, `posx-demo-store`, `posx-eume-store`,
`posx-frido-store`, `posx-frido-b2b-store`, `posx-frido-mobility-store`.
Verify against `posx-mokobara-store`/`posx-ugaoo-store`, which don't have
this line and install cleanly — diff their `package.json` dependency block
against a broken one to confirm nothing else needs to change.
**Effort: ~1 hour total (mechanical, same fix x6). Unblocks:** `npm audit`,
dependency-cruiser, and any future mutation-testing pass on these 6 repos.

### 2. Wire `posx-mokobara-backend/.github/workflows/quality.yml` into the other 24 gated-but-not-enforced repos
It already exists, already works, and is already proven (162/162 tests
passing on the one repo that has it). For each of the other 24: copy the
workflow, point `test:unit`/`test` at that repo's actual script name (some
are `test`, some are `test:unit` — see `testquality_runs.csv`'s
`script_used` column for the exact name per repo), adjust `lint:changed` if
that script doesn't exist yet (add a minimal version if not — the existing
one's "lint changed lines only, full-repo count visible but non-blocking"
pattern is exactly right for a codebase with an unknown-but-nonzero
existing lint debt).
**Effort: ~2-3 days for all 24** (mostly copy-and-adjust; the admin repos
are closer to a direct copy since they share the same `vitest --run`
script name already — §1's duplication cuts the other way here, for once).
**This is the single highest-leverage fix in this whole report**: every
other quality finding downstream of "nothing blocks a bad merge" gets
caught here, going forward, for free.

### 3. Fix the 3 concrete, isolated bugs already found (§4)
- `posx-frido-b2b-backend/jest.config.js`: remove or restore the missing
  `./integration-tests/setup.js` reference. One-line diagnosis, check
  which was intended before choosing.
- `posx-mokobara-admin`'s vitest config: add `tests/e2e/**` to `exclude` so
  Playwright specs stop being collected as vitest tests. Also wire
  `test:e2e` (already exists as a script, per `posx-mokobara-admin`'s
  `package.json`) into a *separate* CI job if Playwright coverage is worth
  keeping.
- `posx-comet-backend`'s address validator (`src/types/validators/online-order-address.ts`
  or wherever the schema is defined, exercised by
  `__tests__/online-order-address.unit.spec.ts:32,100`): decide whether the
  test or the implementation is wrong — the test expects empty-string
  defaults for optional address fields; the implementation currently
  returns `success: false`. This is a live order-address code path.
**Effort: half a day total, once someone with product context picks the
right side of each fix.**

## Do this month

### 4. Fix the shared i18n test in the 4 admin repos where it's currently red (§4)
`demo-admin`, `eume-admin`, `frido-mobility-admin`, `mokobara-admin` each
have their own missing/extra translation keys — this is real,
per-brand-content work (someone has to fill in the actual missing
translations), not a code fix. Do it now while item #2's CI gate isn't live
yet on these repos; once it is, this exact class of drift will be caught at
PR time instead of silently, going forward.

### 5. Write tests for the 3 repos where the harness exists but nothing does
`posx-demo-backend`, `posx-frido-mobility-backend`,
`posx-mokobara-clearance-backend`: `test:unit` runs cleanly, matches the
same `testMatch` pattern every other backend uses, and finds zero files.
These are also 3 of the 5 highest bus-factor-risk repos (§9) — small,
single/dual-author, newly launched. Backfilling even the highest-value 5-10
unit tests per repo (start with whatever's closest to `posx-comet-backend`'s
failing address-validator pattern, since that's a proven real defect class)
is more valuable here than broad coverage.

### 6. Extract the byte-identical shared code into real internal packages (§1)
This is the actual fix for the root cause behind §1, §4's repeated i18n
failure, and the §7 hotspot repeated across 4 store repos. Concretely, from
`exact_duplicate_files.csv`'s highest-repo-count groups:
- `@posx/backend-shared`: `src/api/middlewares.ts`, `src/lib/puppeteer.ts`,
  `src/lib/nodemailer.ts`, the `src/links/*` relationship declarations,
  `src/modules/shopify-collection/index.ts` — all identical across all 9
  backends today, meaning extracting them changes zero behavior.
- `@posx/eslint-config`: the `eslint.config.js` identical across all 11
  stores.
- `@posx/i18n-validation`: the shared translation-schema test itself,
  published once so a schema change updates the check everywhere instead
  of needing 8 manual copies to stay in sync (this is what let 4 of 8 drift
  silently in the first place).

**Do not** attempt this for `medusa-config.ts` — confirmed by direct diff
(§1) that despite jscpd flagging a shared block, the files carry real,
necessary per-tenant differences (module lists, Redis config). Extract only
what §1's *sha256* list (not the jscpd block list) confirms is actually
identical.
**Effort: 1-2 weeks for a first package** (`@posx/backend-shared`, highest
value, most files already 100% identical so the extraction itself is close
to a pure `git mv` + import-path update, not a rewrite). Don't scope all
three packages into one project — ship the highest-value one, measure
whether the pattern holds up in practice, then decide on the rest.

## Ongoing, not a one-time task

### 7. Re-run this tool's `escape` and `testquality` modules monthly
§6's trend (escape rate improving) and §2's gate rollout (item #2) are both
things a single snapshot can't confirm stayed true. `python3 cli.py analyze
/path/to/posx --modules escape,ci_gates,testquality` is cheap enough to run
monthly and catch a regression in either direction before it's a surprise.

### 8. `posx-kb` needs an owner or an archive decision
1 author, 5 commits, no CI, no package.json test infra of any kind. Not
urgent, but it's the one repo in the portfolio with no signal of anyone
else being able to pick it up if that author leaves.

## What this roadmap deliberately does not include

- **A full monorepo consolidation** (the Button engagement's 180→5 plan).
  posx is 26 repos with a much shallower ops/config sprawl (5.9% vs
  Button's 36%) — the problem here is duplicated *application* code across
  independently-deployed brand instances, not infrastructure sprawl across
  one company's internal platform. Extracting shared packages (item #6)
  solves the actual duplication without forcing 8 independently-deployed
  client storefronts into one repo, which would trade a code problem for a
  deployment-coupling problem.
- **Mutation testing.** Attempted (Stryker, scoped to one small
  well-tested module) and abandoned after three real, distinct environment
  failures (npx package isolation, a missing `typescript` peer resolution,
  a stale cached binary name collision) rather than force a fourth fix for
  what was a bonus verification, not a core finding. The dynamic
  pass/fail results in §4 already give real, executed evidence — mutation
  testing would add a further "are the passing tests behaviorally
  meaningful" layer on top, worth revisiting with a clean local Stryker
  install (not `npx`) rather than in the remaining time on this pass.
