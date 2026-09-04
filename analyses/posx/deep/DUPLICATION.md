# posx — *Duplication*

*Two independent measurements, kept separate deliberately: `jscpd` finds **block-level**
duplication (>=10 lines / >=70 tokens) across the whole portfolio in one pass; a direct sha256
hash of whole-file contents finds **exact, byte-identical** files. A file can share a jscpd
block with another file while differing everywhere else -- conflating the two would overclaim
whole-file identity from a partial match (a real mistake caught and corrected while building
this tool by running an actual `diff`; see `docs/METHODOLOGY.md`). Data:
`duplication_summary.json`, `duplication_clones.csv`, `exact_duplicate_files.csv`,
`exact_duplicate_summary.json`.*

## 1. Block-level duplication (jscpd)

**63.6%** of all lines are part of a duplicated block. **15988** of 17658 clone pairs are cross-repo (not within a single repo).

## 2. Exact, byte-identical files

**3001** files are byte-identical across two or more repos at the same relative path (of 26 repos scanned) -- the strongest possible signal for extracting a shared package. Max repos sharing one identical file: **9**.

| Relative path (or hash group) | Repos sharing it | Repos |
|---|---|---|
| src/admin/vite-env.d.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/admin/tsconfig.json | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/order-detail-store-detail-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/footfall-employee-details.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/order-product-shopify-variant-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/footfall-store-details.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/shopify-collection-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/shopify-product-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/order-detail-employee-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/order-detail-payment-detail-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/links/shopify-variant-link.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/lib/puppeteer.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/lib/nodemailer.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/modules/shopify-collection/index.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |
| src/modules/shopify-collection/service.ts | 9 | posx-comet-backend, posx-demo-backend, posx-eume-backend, posx-frido-b2b-backend, posx-frido-backend, posx-frido-mobility-backend, posx-mokobara-backend, posx-mokobara-clearance-backend, posx-ugaoo-backend |

## 3. Honest limitations

- jscpd's percentage is inflated by legitimate per-project boilerplate (lockfiles, generated
  config) that isn't a real duplication problem -- the exact-match list above is the stricter,
  more actionable signal.
- Exact-match groups only catch identical files at the *same relative path*. Two files with
  identical content at different paths (e.g. one repo renamed its copy) are not detected here.

*Raw data: `duplication_clones.csv`, `exact_duplicate_files.csv`.*
