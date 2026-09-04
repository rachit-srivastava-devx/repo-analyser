# posx — *Security*

*`gitleaks` over **complete git history** per repo (a secret removed in a later commit is
still permanently readable by anyone with clone access) + `semgrep` (`p/security-audit` +
`p/secrets`) over the current tree. Data: `security_secrets.csv`, `security_semgrep.csv`,
`security_summary.json`.*

## 1. Secret-history scan (gitleaks)

**80 findings across 8
repos** (26 repos scanned):

| Rule | Count |
|---|---|
| generic-api-key | 37 |
| curl-auth-header | 20 |
| shopify-access-token | 17 |
| aws-access-token | 3 |
| shopify-custom-access-token | 2 |
| jwt | 1 |

By repo:

| Repo | Findings |
|---|---|
| posx-mokobara-backend | 29 |
| posx-comet-backend | 24 |
| posx-ugaoo-backend | 11 |
| posx-kb | 10 |
| posx-frido-store | 2 |
| posx-mokobara-clearance-backend | 2 |
| posx-eume-backend | 1 |
| posx-mokobara-store | 1 |

**Every rule-format match above is a starting point, not a confirmed secret** -- generic-entropy
rules in particular need a manual look. This tool does not attempt to validate or use any
discovered credential against a live provider API (out of scope regardless of feasibility); it
also checks whether each is still present in current `HEAD` vs. history-only where that
distinction changes the remediation urgency -- see the raw CSV's `commit` column and check with
`git grep <secret-prefix> HEAD` in the affected repo.

## 2. Code-pattern scan (semgrep)

**2 findings.**

| Severity | Count |
|---|---|
| WARNING | 2 |

## 3. Honest limitations

- gitleaks' `generic-api-key` and `curl-auth-header` rules are pattern/entropy-based and will
  include false positives (test fixtures, non-secret high-entropy strings). Only
  format-confirmed rules (`aws-access-token`, `shopify-access-token`, `jwt`, etc.) are close to
  self-verifying by their prefix alone.
- semgrep's ruleset here (`p/security-audit`, `p/secrets`) is broad but not exhaustive --
  absence of a finding is not proof of absence of a vulnerability class the ruleset doesn't cover.

*Raw data: `security_secrets.csv`, `security_semgrep.csv`.*
