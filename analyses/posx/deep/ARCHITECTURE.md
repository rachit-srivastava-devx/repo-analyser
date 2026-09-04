# posx — *Architecture*, HLD & Memory Graph

*Built via `codebase-memory-mcp` (LSP-based call/usage resolution -- a real persistent code
knowledge graph, i.e. a "memory graph" of the codebase, not a static-analysis approximation of
one). This capture: 8199 nodes, 14599 edges across 3 repo(s): posx-mokobara-backend, posx-mokobara-admin, posx-mokobara-store. **Caveat, said plainly**: this capture used an
interactive MCP tool available in a Claude Code session, not a subprocess chronicle-analyzer's
CLI can invoke standalone on any machine -- treat this section as a snapshot from whatever
repos were indexed when it was captured, not a rerunnable module output the way every other
section in this report is. Re-capture it for a different repo set by indexing with
`codebase-memory-mcp` and re-saving `architecture_graph.json`/`shared_deps.json` in this
format -- see `docs/METHODOLOGY.md`.*

## 1. Inter-repo connectivity: measured, not assumed

The tool's own cross-repo-intelligence mode matches HTTP/async/gRPC/GraphQL/tRPC calls across
indexed projects. Result across 11 projects: **0
cross-repo calls found** (HTTP: 0, async: 0,
channel: 0, gRPC: 0, GraphQL: 0).

**Most-shared internal signal**: `moment` is used by **25 of 26 repos** -- check whether it is a real shared internal package (worth checking its registry listing/publish count) rather than assuming no cross-repo dependency exists.

| Package | Repos using it |
|---|---|
| moment | 25 |
| axios | 23 |
| zod | 18 |
| react | 17 |
| react-dom | 17 |
| @devxcommerce/shopify | 17 |
| cmdk | 16 |
| @hookform/resolvers | 16 |
| date-fns | 16 |
| react-hook-form | 16 |
| @tanstack/react-query | 9 |
| nodemailer | 9 |

## 2. HLD: layers and boundaries (posx-mokobara-backend)

| Package | Layer | Why |
|---|---|---|
| api | entry | has entry points, only outbound calls |
| jobs | internal | fan-in=3, fan-out=25 |
| json | api | has HTTP route definitions |
| lib | core | high fan-in (879 in, 7 out) |
| modules | core | high fan-in (113 in, 37 out) |
| subscribers | entry | only outbound calls |
| workflows | entry | only outbound calls |

| From | To | Call count |
|---|---|---|
| api | lib | 809 |
| api | modules | 72 |
| modules | lib | 37 |
| subscribers | lib | 23 |
| subscribers | modules | 16 |
| jobs | modules | 15 |
| jobs | lib | 10 |
| lib | modules | 7 |
| workflows | modules | 3 |
| api | jobs | 3 |

`api -> lib`: 809 calls -- the largest internal boundary found in this capture; cross-check against `DUPLICATION.md` for whether that target package is also duplicated across repos.

## 3. LLD: the actual hotspot functions and real clusters

| Function | Fan-in (callers) |
|---|---|
| api-response.sendApiResponse | 249 |
| api-response.createSuccessResponse | 243 |
| api-response.createErrorResponse | 240 |
| calculate-online-coupon-discount.warn | 46 |
| calculate-store-coupon-discount-step.warn | 45 |
| calculate-online-coupon-discount.log | 43 |
| build-summary.buildSummary | 23 |
| UnicommerceService.init | 23 |
| get-s3-file-path-for-order.getS3FilePath | 18 |
| date-utils.startOfDayIST | 14 |

`sendApiResponse` (249 callers) is the single most depended-upon function found in this capture.

Real Leiden-detected clusters (the de-facto modules, which cut across folder layout):

| Cluster | Members | Cohesion | Represents |
|---|---|---|---|
| 10 | 204 | 0.76 | sendApiResponse, createSuccessResponse, createErrorResponse |
| 6 | 107 | 0.75 | log, init, init |
| 0 | 58 | 0.5 | warn, PUT, POST |
| 50 | 46 | 0.69 | redeem, writeAudit, cancelVoucher |
| 3 | 44 | 0.89 | call, redeem, cancelRedeem |
| 7 | 42 | 0.69 | startOfDayIST, buildInwardsDigest, endOfDayIST |
| 2 | 34 | 0.87 | POST, evaluateShopifyOffer, evaluateRetailOffer |
| 64 | 24 | 0.92 | hasPermissionByRole, hasPermission, resolveActorEmployee |

## 4. Honest limitations

- Representative, not exhaustive: the indexed repo(s) stand in for any structurally similar
  repos elsewhere in the portfolio (check `DUPLICATION.md` for which repos actually share
  structure before generalizing this section to them).
- Cross-repo-intelligence only detects *code-level* calls (HTTP/async/RPC). It cannot detect
  connectivity through shared infrastructure with no code reference -- this analysis has no
  runtime-wiring export (e.g. a CTO-approved production env-var dump) for this target, so
  infra-level connectivity (if any) is unverified, not ruled out.

*Raw data: `architecture_graph.json`, `shared_deps.json`.*
