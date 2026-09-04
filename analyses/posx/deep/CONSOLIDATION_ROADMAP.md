# posx — Consolidation & *Way-Forward* Roadmap

*Synthesizes every other category into one ranked list and a prioritized action list. The risk
score (`synthesize.py`) is a weighted, min-max-normalized combination of escape rate, hotspot
concentration, duplication involvement, missing CI gates, test failures, security findings, and
bus-factor -- a heuristic for *prioritization*, stated as such, not a ground truth. Data:
`risk_ranking.csv`, `risk_weights.json`.*

## 1. Highest-priority repos, by composite risk score

| Repo | Risk score | Escapes | Top-5 hotspot sum | Exact dup files | CI gate missing | Security findings |
|---|---|---|---|---|---|---|
| posx-comet-backend | 0.5782 | 801 | 16233 | 245 | True | 24 |
| posx-mokobara-store | 0.5569 | 740 | 54442 | 107 | True | 1 |
| posx-mokobara-backend | 0.5307 | 979 | 40200 | 252 | False | 29 |
| posx-mokobara-admin | 0.5218 | 267 | 11542 | 1634 | True | 1 |
| posx-comet-store | 0.512 | 917 | 29891 | 123 | True | 0 |
| posx-eume-store | 0.4394 | 235 | 57587 | 224 | True | 0 |
| posx-frido-backend | 0.4362 | 666 | 17015 | 486 | True | 0 |
| posx-eume-admin | 0.4278 | 41 | 4375 | 1653 | True | 0 |
| posx-demo-admin | 0.42 | 1 | 835 | 1669 | True | 0 |
| posx-frido-mobility-admin | 0.4188 | 0 | 1133 | 1731 | True | 0 |

See `risk_weights.json` for the exact weights behind this ranking -- change them if you weigh
these dimensions differently; the raw per-dimension numbers underneath are the actual evidence.

## 2. Recommended action order

1. **Rotate credentials found in git history first.** 80 secret-shaped findings across 8 repos -- see `SECURITY.md`. This is a today action, independent of everything else here.

2. **Wire CI to actually run tests on the 24 repos where it currently doesn't.** A working, proven pattern already exists in this portfolio: posx-mokobara-backend. This is the single highest-leverage fix available: every other quality finding downstream of 'nothing blocks a bad merge' gets caught here, going forward, for free.

3. **Extract the byte-identical shared code into real internal packages.** 3001 files are identical across multiple repos (up to 9 at once) -- see `DUPLICATION.md` for the exact file list. Extracting only what the exact-match list confirms identical changes zero behavior; verify with `diff` before assuming a jscpd block match means the same for any file not on the exact-match list.

4. **3 repos have a working test harness and zero tests behind it.** Cheaper to fix than repos with no harness at all -- the wiring already works, someone just needs to write the tests.

5. **72 candidate toil clusters** (3060 commits) are repeated, mechanical work concentrated by location -- see `EFFORT_ALLOCATION.md` for the ranked list. Each is worth a human read before committing to a specific fix; this tool does not size the remediation effort.

## 3. Honest limitations

- The composite risk score is dominated in part by raw activity/scale (an old, high-churn repo
  accumulates more escapes and hotspot mass than a small quiet one just by having existed
  longer and shipped more) -- it is a prioritization aid for where to look first, not a
  cleanly isolated "badness" measure. Read the underlying per-dimension columns before acting
  on rank alone.
- This report does not estimate effort or ROI for any recommendation -- that requires product
  and team context this tool does not have. It tells you what the data shows and where to look;
  the sizing and sequencing judgment is a human decision.

*Raw data: `risk_ranking.csv`, `risk_weights.json`.*
