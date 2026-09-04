# posx — Dependency *Health*

*`osv-scanner` (Google's cross-ecosystem OSV-database scanner) reads each repo's lockfile
directly against known CVE records -- a different, deeper question than gitleaks (committed
secrets) or semgrep (code patterns): are the *dependencies themselves* known-vulnerable.
`npm outdated` gives current vs. latest per package. `npm audit` was tried and dropped (hung
repeatedly on a live registry round-trip in this environment); osv-scanner is faster and
already confirmed working -- see docs/METHODOLOGY.md. Data: `deps_cves.csv`, `deps_outdated.csv`.*

## 1. Known-CVE findings

**2636 findings across 18 repos.**

| Severity | Count |
|---|---|
| critical | 63 |
| high | 1241 |
| medium | 1107 |
| low | 225 |

| Repo | CVE findings |
|---|---|
| posx-demo-backend | 543 |
| posx-comet-backend | 308 |
| posx-ugaoo-backend | 295 |
| posx-frido-b2b-backend | 192 |
| posx-frido-mobility-backend | 192 |
| posx-frido-backend | 161 |
| posx-ugaoo-admin | 139 |
| posx-mokobara-store | 102 |
| posx-ugaoo-store | 98 |
| posx-frido-admin | 94 |
| posx-frido-b2b-admin | 94 |
| posx-mokobara-admin | 94 |

## 2. Package staleness

**772 outdated packages, 419 a full major version behind** (current vs. latest):

| Repo | Package | Current | Latest |
|---|---|---|---|
| posx-comet-admin | @dnd-kit/sortable | 8.0.0 | 10.0.0 |
| posx-comet-admin | @hookform/resolvers | 3.4.2 | 5.9.1 |
| posx-comet-admin | @tanstack/react-table | 8.20.5 | 9.2.4 |
| posx-comet-admin | @types/node | 20.17.24 | 26.4.1 |
| posx-comet-admin | @types/react | 18.3.18 | 19.2.18 |
| posx-comet-admin | @types/react-dom | 18.3.5 | 19.2.7 |
| posx-comet-admin | @vitejs/plugin-react | 4.2.1 | 6.1.1 |
| posx-comet-admin | cmdk | 0.2.1 | 1.1.1 |
| posx-comet-admin | date-fns | 3.6.0 | 4.4.0 |
| posx-comet-admin | i18next | 23.7.11 | 26.4.2 |
| posx-comet-admin | i18next-browser-languagedetector | 7.2.0 | 8.2.1 |
| posx-comet-admin | i18next-http-backend | 2.4.2 | 4.0.2 |

## 3. Honest limitations

- osv-scanner flags a *known* CVE affecting the resolved version -- it does not confirm the
  vulnerable code path is actually reachable/exploited in this codebase's usage of the package.
- "Major version behind" is a proxy for staleness/upgrade risk, not itself a defect --
  some majors are trivial bumps, others are breaking rewrites. Triage by package, not by count.

*Raw data: `deps_cves.csv`, `deps_outdated.csv`.*
