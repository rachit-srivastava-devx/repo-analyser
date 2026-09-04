# posx — Code *Quality* (Static Analysis)

*Each repo's own linter, run with its own config -- never a config this tool invents. ESLint
via the repo's local `node_modules/.bin/eslint` (not `npx`, which cannot resolve a project's
plugin-dependent config). ruff for Python, staticcheck for Go. Data: `lint_quality.csv`.*

## 1. Results

**7 of 26
repos actually linted** (19 skipped -- see below).
**4165 errors, 218 warnings** total.

| Repo | Linter | Errors | Warnings | Top rules |
|---|---|---|---|---|
| posx-mokobara-backend | eslint | 2634 | 127 | @typescript-eslint/no-explicit-any:1824;@typescript-eslint/ban-ts-comment:247;@t |
| posx-frido-backend | eslint | 568 | 13 | @typescript-eslint/no-explicit-any:368;@typescript-eslint/ban-ts-comment:102;@ty |
| posx-frido-mobility-backend | eslint | 389 | 0 | @typescript-eslint/no-explicit-any:211;@typescript-eslint/ban-ts-comment:91;@typ |
| posx-frido-b2b-backend | eslint | 259 | 0 | @typescript-eslint/no-explicit-any:145;@typescript-eslint/ban-ts-comment:58;@typ |
| posx-mokobara-store | eslint | 192 | 39 | @typescript-eslint/no-explicit-any:183;react-hooks/exhaustive-deps:31;@typescrip |
| posx-ugaoo-store | eslint | 119 | 37 | @typescript-eslint/no-explicit-any:106;react-hooks/exhaustive-deps:30;@typescrip |
| posx-kb | eslint | 4 | 2 | react-hooks/set-state-in-effect:3;@typescript-eslint/no-unused-vars:2;react-hook |

## 2. Why repos were skipped

19 repos could not be linted -- almost always because the
repo's own `package.json` declares a `lint` script that calls a linter never installed as a
real dependency (`eslint not in node_modules/.bin`). That is itself a finding: a lint script
that cannot run is not a quality gate, it is a broken promise in `package.json`.

## 3. Honest limitations

- Different repos may run different rule strictness (each uses its own config) -- error counts
  are not directly comparable across repos with different configs.

*Raw data: `lint_quality.csv`.*
