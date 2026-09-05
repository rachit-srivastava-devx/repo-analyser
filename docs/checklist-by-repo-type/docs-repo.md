# Docs Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **Majority .md/.mdx/.rst; docusaurus.config.js, mkdocs.yml, conf.py (Sphinx), or .vitepress present; no app source** | `cloc`, find . -iname "*.md" \| wc -l |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Content freshness/staleness** | a last-verified date compared against the last-changed date of the code/feature it documents. | `front-matter last_reviewed + CI check`, `git log staleness script` |
| **Broken internal/external link detection** | dead hyperlinks and anchors, both within the doc set and out to external sites. | `markdown-link-check`, `lychee` |
| **Doc-to-code drift** | documented signatures, CLI flags, config options, and screenshots still match current shipped behavior. | `doctest/MDX executable examples`, `CLI --help snapshot tests` |
| **Style/terminology consistency linting** | house style and terminology enforced automatically instead of relying on reviewer memory. | `Vale`, `alex`, `textlint` |
| **Search & discoverability** | pages are indexed, cross-linked, and findable rather than orphaned with zero inbound links or search hits. | `Pagefind`, `Typesense (self-hosted)` |
| **Ownership clarity per section** | every page/section has a named owning team so a stale or wrong doc has an accountable fixer. | `codeowners-validator`, `front-matter owner field` |
| **Structural build validation & redirects** | the docs site builds with zero warnings, nav entries aren't orphaned/duplicated, moved pages redirect instead of 404ing. | `MkDocs/Docusaurus build --strict`, `htmltest` |
| **Versioned-docs alignment** | for multi-version products, the docs version served matches the supported release line, with no cross-version behavior bleed. | `Docusaurus versioned docs`, `mike (MkDocs)` |
| **On-page reader feedback** | direct star-rating/comment widgets per doc page routed to the docs team, unlike indirect search-behavior signals alone. | `custom feedback widget + log`, `Fider`, `Umami` |
| **Accessibility/alt-text coverage** | systematic alt-text coverage and WCAG compliance tracked across the entire doc set, not just the app UI. | `axe-core`, `Pa11y`, `custom alt-text audit script` |
| **Readability scoring** | Flesch-Kincaid grade-level scoring of prose complexity, distinct from word-choice/terminology rules. | `Vale ReadingLevel rule`, `textstat` |
