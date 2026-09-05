# Browser Extension Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `manifest.json` at root with a `manifest_version` key, no server-side code | `jq .manifest_version manifest.json` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Manifest / permission linting** | requested permissions are checked against what the extension's code actually uses, flagging anything broader than justified. | `web-ext lint (Mozilla)` |
| **MV3 remote-code / CSP compliance** | no eval or remotely-hosted executable logic ships in the bundle, since Manifest V3 makes this store-rejection grounds, not just a lint warning. | `Chrome Web Store automated MV3 review` |
| **Privacy-disclosure parity** | the store listing's declared data-collection practices match what the shipped code actually does, the same disclosure-vs-reality check mobile apps need. | `Chrome Web Store Developer Dashboard` |
| **Bundled-secret scanning** | API keys or tokens embedded in shipped JS are caught before release, since a browser extension's client-side code is trivially unpacked by any installer. | `TruffleHog` |
| **Update-channel integrity** | the store-hosted auto-update path is the only trust boundary an install has, so its update_url and signing are reviewed against store policy rather than assumed safe by default. | `store policy review of update_url` |
