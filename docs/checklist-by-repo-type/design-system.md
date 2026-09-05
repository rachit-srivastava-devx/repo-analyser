# Design System / Component Library Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `.storybook/` config plus a package that ships only UI components with no app entry point, often paired with a Style Dictionary/tokens config | `test -d .storybook` · `find . -iname "tokens*.json"` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Visual regression on every component story** | every documented component state is screenshot-diffed on each change, since "looks right" is a correctness property here that no generic library audit checks. | `Chromatic` *(keyed)*, `Percy` *(keyed)* |
| **Automated per-component accessibility scoring** | every component story is scanned for accessibility violations as part of the same pipeline that catches visual regressions, not audited by hand once per release. | `axe-core (via Storybook a11y addon)` |
| **Single-source-of-truth design tokens** | color, spacing, and type tokens are generated from one source into every consuming platform (web/iOS/Android), so a token update can't drift into three different values across platforms. | `Style Dictionary` |
| **Design-to-code drift detection** | the Figma source of a component is checked against what's actually shipped in code, catching the slow drift that accumulates once a component is "done" and nobody rechecks it. | `Figma Code Connect` |
| **Change-impact analysis across consuming apps** | every app that consumes the design system is checked for visual breakage before a token or component version bump ships, instead of finding out from a downstream bug report. | `Chromatic TurboSnap` *(keyed)* |
